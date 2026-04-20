import io
import os
import re
import json
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple, Optional

from pymongo import MongoClient
import google.generativeai as genai

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

# =========================================================
# CONFIG
# =========================================================
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://thanu582:Thanu%402004@healthcareai.ivdrwbz.mongodb.net/")
MONGODB_DB = os.getenv("MONGO_DB_NAME", "News")
MONGODB_COLLECTION = os.getenv("MONGO_COLLECTION_NAME", "PoliticalNews")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyA-XEPLBWgFbveEaMBjH7mVk6ktspOVryY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


# =========================================================
# HELPERS
# =========================================================
def clean_text(value: Any) -> str:
    if value is None:
        return "Data not available"
    if isinstance(value, list):
        return "; ".join(clean_text(v) for v in value if v is not None) or "Data not available"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    return text if text else "Data not available"


MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def extract_year(date_str: str) -> int:
    if not date_str:
        return 0
    m = re.search(r"(19|20)\d{2}", date_str)
    return int(m.group(0)) if m else 0


def extract_month(date_str: str) -> int:
    if not date_str:
        return 12
    lower = date_str.lower()
    for name, num in MONTHS.items():
        if re.search(rf"\b{name}\b", lower):
            return num
    return 12


def extract_day(date_str: str) -> int:
    if not date_str:
        return 31
    m = re.search(r"\b(\d{1,2})\b", date_str)
    if m:
        day = int(m.group(1))
        if 1 <= day <= 31:
            return day
    return 31


def sortable_key(article: Dict[str, Any]) -> Tuple[int, int, int, int]:
    date_str = clean_text(article.get("date"))
    return (
        extract_year(date_str),
        extract_month(date_str),
        extract_day(date_str),
        int(article.get("id", 0) or 0),
    )


def normalize_person_key(subject: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", subject.strip().lower()).strip("_")


# =========================================================
# MONGODB
# =========================================================
def load_document_from_mongodb(subject: str) -> Dict[str, Any]:
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI is not set.")

    person_key = normalize_person_key(subject)

    client = MongoClient(MONGODB_URI)
    collection = client[MONGODB_DB][MONGODB_COLLECTION]

    candidates = [
        {"person_key": person_key},
        {"subject_name": subject},
        {"subject": subject},
        {"name": subject},
        {"person_name": subject},
    ]

    doc: Optional[Dict[str, Any]] = None
    for query in candidates:
        doc = collection.find_one(query)
        if doc:
            break

    if not doc:
        raise ValueError(f"No MongoDB document found for subject='{subject}' / person_key='{person_key}'")

    return doc


# =========================================================
# ANALYTICS FROM DATASET ONLY
# =========================================================
def build_dataset_summary(doc: Dict[str, Any], subject: str) -> Dict[str, Any]:
    articles = doc.get("articles", []) or []
    articles = sorted(articles, key=lambda x: int(x.get("id", 0) or 0))

    if not articles:
        raise ValueError("The MongoDB document has no articles array.")

    person_key = clean_text(doc.get("person_key"))
    if person_key == "Data not available":
        person_key = normalize_person_key(subject)

    subject_name = clean_text(
        doc.get("subject_name")
        or doc.get("subject")
        or doc.get("name")
        or doc.get("person_name")
        or subject
    )

    years = [
        extract_year(clean_text(a.get("date")))
        for a in articles
        if extract_year(clean_text(a.get("date"))) > 0
    ]
    min_year = min(years) if years else "Data not available"
    max_year = max(years) if years else "Data not available"

    sources = Counter(clean_text(a.get("source")) for a in articles)
    categories = Counter(clean_text(a.get("category")) for a in articles)
    confidences = Counter(clean_text(a.get("confidence")) for a in articles)
    source_types = Counter(clean_text(a.get("sourceType")) for a in articles)

    decade_buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    year_counts = Counter()
    month_year_counts = Counter()

    for a in articles:
        y = extract_year(clean_text(a.get("date")))
        if y:
            decade_start = (y // 10) * 10
            decade_label = f"{decade_start}-{decade_start + 9}"
            decade_buckets[decade_label].append(a)
            year_counts[y] += 1
            month_year_counts[(y, extract_month(clean_text(a.get("date"))))] += 1
        else:
            decade_buckets["Undated"].append(a)

    peak_years = year_counts.most_common(5)
    peak_month_years = month_year_counts.most_common(8)

    entity_map = {
        "business": [],
        "advocacy": [],
        "politics": [],
        "government": [],
        "media": [],
        "awards": [],
    }

    def infer_period(matches: List[Dict[str, Any]]) -> str:
        ys = [
            extract_year(clean_text(x.get("date")))
            for x in matches
            if extract_year(clean_text(x.get("date"))) > 0
        ]
        if not ys:
            return "Data not available"
        return f"{min(ys)}-{max(ys)}" if min(ys) != max(ys) else str(min(ys))

    def add_entity(bucket: str, name: str, role: str, note: str, matches: List[Dict[str, Any]]):
        if not matches:
            return
        entity_map[bucket].append({
            "name": name,
            "role": role,
            "period": infer_period(matches),
            "note": note,
        })

    def find_matches(*terms: str) -> List[Dict[str, Any]]:
        matches = []
        lowered_terms = [t.lower() for t in terms]
        for a in articles:
            hay = " ".join([
                clean_text(a.get("headline")).lower(),
                clean_text(a.get("summary")).lower(),
                clean_text(a.get("category")).lower(),
                clean_text(a.get("source")).lower(),
            ])
            if any(term in hay for term in lowered_terms):
                matches.append(a)
        return matches

    add_entity(
        "business",
        "Business / Corporate Entities",
        "Subject-linked business coverage",
        "Derived from business, corporate, ownership, deal, finance, or company-related articles.",
        find_matches("business", "company", "owner", "finance", "investment", "corporate", "deal", "profit", "market"),
    )
    add_entity(
        "advocacy",
        "Advocacy / Community Network",
        "Subject-linked civic or community activity",
        "Derived from advocacy, nonprofit, community, foundation, education, or support initiatives.",
        find_matches("advocacy", "community", "nonprofit", "foundation", "charity", "campaign", "support", "activism"),
    )
    add_entity(
        "politics",
        "Political Affiliations / Activity",
        "Political coverage involving the subject",
        "Derived from elections, party, donor, mayor, governor, campaign, senate, congress, or political controversy.",
        find_matches("politic", "campaign", "election", "republican", "democrat", "mayor", "governor", "senate", "congress", "white house"),
    )
    add_entity(
        "government",
        "Government Roles / Institutions",
        "Government-linked activity or references",
        "Derived from appointments, public office, administration, commission, or agency-related coverage.",
        find_matches("commission", "government", "administration", "agency", "department", "public office"),
    )
    add_entity(
        "media",
        "Media Presence",
        "Press, interview, or broadcast visibility",
        "Derived from interview, television, cnn, fox, news appearance, broadcast, or media references.",
        find_matches("interview", "television", "cnn", "fox", "broadcast", "media", "podcast", "press"),
    )
    add_entity(
        "awards",
        "Awards / Recognition",
        "Recognition or honor-related coverage",
        "Derived from awards, honors, recognition, recipient, or achievement-related articles.",
        find_matches("award", "honor", "recognition", "recipient", "achievement", "prize"),
    )

    return {
        "subject_name": subject_name,
        "person_key": person_key,
        "articles": articles,
        "year_range": f"{min_year}-{max_year}" if min_year != "Data not available" and max_year != "Data not available" else "Data not available",
        "min_year": min_year,
        "max_year": max_year,
        "total_articles": len(articles),
        "unique_sources": len(sources),
        "top_sources": sources.most_common(12),
        "top_categories": categories.most_common(12),
        "confidence_breakdown": dict(confidences),
        "source_type_breakdown": dict(source_types),
        "decade_buckets": dict(sorted(decade_buckets.items())),
        "peak_years": peak_years,
        "peak_month_years": peak_month_years,
        "entity_map": entity_map,
    }


# =========================================================
# GEMINI GENERATION (EXACT PROMPT STRUCTURE)
# =========================================================
def build_prompt(summary: Dict[str, Any]) -> str:
    compact_articles = []
    for a in summary["articles"]:
        compact_articles.append({
            "id": a.get("id"),
            "date": clean_text(a.get("date")),
            "source": clean_text(a.get("source")),
            "headline": clean_text(a.get("headline")),
            "url": clean_text(a.get("url")),
            "summary": clean_text(a.get("summary")),
            "category": clean_text(a.get("category")),
            "confidence": clean_text(a.get("confidence")),
            "sourceType": clean_text(a.get("sourceType")),
        })

    return f"""
You are a senior intelligence analyst and executive report writer specializing in media archives, structured intelligence reports, and entity mapping.

TASK:
Generate JSON only for a PDF-ready intelligence report titled:
"{summary['subject_name']} - Comprehensive Media Archive & Strategic Profile"

STRICT RULES:
- Use only the provided dataset.
- Do NOT assume or infer missing facts beyond the dataset.
- If data is missing, write exactly: "Data not available".
- Preserve dates, sources, wording, and confidence labels.
- Keep paragraphs short.
- Formal, executive tone.
- Return VALID JSON only. No markdown fences.

Return this exact JSON structure:
{{
  "title": "...",
  "sections": {{
    "executive_summary": "200-300 words",
    "executive_takeaways": [
      "Strategic Takeaway 1: ...",
      "Strategic Takeaway 2: ...",
      "Strategic Takeaway 3: ...",
      "Key Insight: ..."
    ],
    "media_coverage_overview": "120-180 words",
    "media_coverage_key_insight": "Key Insight: ...",
    "peak_coverage_analysis": [
      {{"label": "...", "explanation": "..."}},
      {{"label": "...", "explanation": "..."}},
      {{"label": "...", "explanation": "..."}}
    ],
    "peak_coverage_key_insight": "Key Insight: ...",
    "decade_breakdown": [
      {{"period": "1989-1999", "summary": "..."}}
    ],
    "thematic_analysis": "120-220 words",
    "thematic_key_insight": "Key Insight: ...",
    "entity_mapping_summary": "80-140 words",
    "methodology_note": "60-120 words",
    "closing_assessment": "120-220 words",
    "due_diligence_questions": [
      "...",
      "...",
      "..."
    ],
    "closing_key_insight": "Key Insight: ..."
  }}
}}

DATASET SUMMARY:
{json.dumps({
    'subject_name': summary['subject_name'],
    'year_range': summary['year_range'],
    'total_articles': summary['total_articles'],
    'unique_sources': summary['unique_sources'],
    'top_sources': summary['top_sources'],
    'top_categories': summary['top_categories'],
    'confidence_breakdown': summary['confidence_breakdown'],
    'source_type_breakdown': summary['source_type_breakdown'],
    'peak_years': summary['peak_years'],
    'peak_month_years': summary['peak_month_years'],
    'entity_map': summary['entity_map'],
}, ensure_ascii=False, indent=2)}

FULL DATASET:
{json.dumps(compact_articles, ensure_ascii=False, indent=2)}
""".strip()


def fallback_report_json(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": f"{summary['subject_name']} - Comprehensive Media Archive & Strategic Profile ",
        "sections": {
            "executive_summary": f"This report summarizes {summary['total_articles']} archived media items spanning {summary['year_range']} for {summary['subject_name']}. The content is derived strictly from the available dataset and is organized for executive review, source trend review, event concentration analysis, and entity mapping. Where details are incomplete in the source data, those gaps are preserved rather than inferred.",
            "executive_takeaways": [
                f"Strategic Takeaway 1: The archive contains {summary['total_articles']} items across {summary['unique_sources']} unique sources.",
                f"Strategic Takeaway 2: Coverage spans {summary['year_range']}.",
                f"Strategic Takeaway 3: The strongest recurring themes are reflected in the top categories and source concentration.",
                "Key Insight: This report is dataset-bound and does not introduce assumptions beyond the archive."
            ],
            "media_coverage_overview": "The available media archive shows the distribution of coverage across sources, categories, and time periods represented in the dataset. The report is designed to preserve the original archive wording and chronology while translating the material into a structured executive format.",
            "media_coverage_key_insight": "Key Insight: The overall media picture should be interpreted through the density of dated records, source repetition, and category concentration.",
            "peak_coverage_analysis": [
                {"label": "Peak Years", "explanation": clean_text(summary.get("peak_years"))},
                {"label": "Peak Months", "explanation": clean_text(summary.get("peak_month_years"))},
                {"label": "Source Concentration", "explanation": clean_text(summary.get("top_sources"))},
            ],
            "peak_coverage_key_insight": "Key Insight: Event clustering is best understood through peak years, peak months, and source concentration.",
            "decade_breakdown": [
                {
                    "period": period,
                    "summary": f"{len(items)} article(s) were identified in this period."
                }
                for period, items in summary.get("decade_buckets", {}).items()
            ] or [{"period": "Data not available", "summary": "Data not available"}],
            "thematic_analysis": "Thematic analysis is constrained to the available categories, summaries, headlines, and sources in the dataset. Themes should be read as evidence-led patterns rather than external judgments.",
            "thematic_key_insight": "Key Insight: Themes in the archive reflect the structure and language of the source records themselves.",
            "entity_mapping_summary": "Entity mapping is produced from repeated patterns in the stored article text and grouped into business, advocacy, politics, government, media, and awards buckets where evidence exists.",
            "methodology_note": "This report is generated directly from the MongoDB archive and uses a strict dataset-only approach. Missing facts are preserved as unavailable rather than guessed.",
            "closing_assessment": "The archive provides a structured basis for executive review, due diligence, and historical media interpretation. Conclusions should remain proportional to the quality and completeness of the stored records.",
            "due_diligence_questions": [
                "Which themes appear most frequently across peak coverage periods?",
                "Which sources dominate the coverage record?",
                "Where do missing fields limit interpretation?"
            ],
            "closing_key_insight": "Key Insight: The report is strongest when used as a structured reading of the archive rather than a substitute for primary source verification."
        }
    }


def generate_report_json_with_gemini(summary: Dict[str, Any]) -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        return fallback_report_json(summary)

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(build_prompt(summary))
        text = response.text.strip()

        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        return json.loads(text)
    except Exception:
        return fallback_report_json(summary)


# =========================================================
# DASHBOARD-BASED SENTIMENT
# =========================================================
def extract_sentiment_from_dashboard(doc: Dict[str, Any]) -> Dict[str, Any]:
    dashboard = (
        doc.get("dashboard_data")
        or doc.get("dashboard")
        or {}
    )

    sentiment = dashboard.get("sentiment") or {}
    peak_positive = dashboard.get("peakPositive") or {}
    peak_negative = dashboard.get("peakNegative") or {}

    def to_float(value: Any, default: float = 0.0) -> float:
        try:
            return round(float(value), 2)
        except Exception:
            return default

    return {
        "articles": [],
        "breakdown": {
            "positive": to_float(sentiment.get("positive"), 0.0),
            "negative": to_float(sentiment.get("negative"), 0.0),
            "neutral": to_float(sentiment.get("neutral"), 0.0),
        },
        "peak_positive": {
            "sentiment_score": clean_text(peak_positive.get("score")),
            "date": clean_text(peak_positive.get("date")),
            "summary": clean_text(peak_positive.get("event")),
            "sentiment_reason": "Derived from dashboard peakPositive",
        } if peak_positive else None,
        "peak_negative": {
            "sentiment_score": clean_text(peak_negative.get("score")),
            "date": clean_text(peak_negative.get("date")),
            "summary": clean_text(peak_negative.get("event")),
            "sentiment_reason": "Derived from dashboard peakNegative",
        } if peak_negative else None,
    }


# =========================================================
# REPORTLAB STYLES
# =========================================================
def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontName="Times-Bold",
        fontSize=18,
        leading=21,
        spaceAfter=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#1b1b1b"),
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=15,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#111111"),
    ))
    styles.add(ParagraphStyle(
        name="SubHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.8,
        leading=13,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor("#222222"),
    ))
    styles.add(ParagraphStyle(
        name="Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        spaceAfter=5,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="SmallBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.4,
        leading=9,
        spaceAfter=0,
    ))
    styles.add(ParagraphStyle(
        name="TableHeader",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.3,
        leading=8.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111111"),
    ))
    styles.add(ParagraphStyle(
        name="BulletBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        leftIndent=10,
        bulletIndent=0,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="Footer",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7,
        alignment=TA_CENTER,
        textColor=colors.grey,
    ))
    return styles


# =========================================================
# PDF HELPERS
# =========================================================
def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(A4[0] / 2.0, 0.4 * inch, f"Page {doc.page}")
    canvas.restoreState()


class ArchiveDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        super().__init__(filename, **kwargs)
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
        )
        template = PageTemplate(id="archive", frames=[frame], onPage=add_page_number)
        self.addPageTemplates([template])


class ArchiveBufferDocTemplate(ArchiveDocTemplate):
    def __init__(self, buffer_obj, **kwargs):
        super().__init__(buffer_obj, **kwargs)


# =========================================================
# TABLE BUILDERS
# =========================================================
def paragraph(text: Any, style) -> Paragraph:
    safe = clean_text(text)
    safe = safe.replace("&", "&amp;")
    return Paragraph(safe, style)


def make_peak_table(items: List[Dict[str, str]], styles) -> Table:
    data = [[
        paragraph("Cluster", styles["TableHeader"]),
        paragraph("Explanation", styles["TableHeader"]),
    ]]
    for item in items:
        data.append([
            paragraph(item.get("label"), styles["SmallBody"]),
            paragraph(item.get("explanation"), styles["SmallBody"]),
        ])
    table = Table(data, colWidths=[1.55 * inch, 4.95 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9edf2")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#a8b0b8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def make_entity_table(title: str, rows: List[Dict[str, str]], styles) -> List[Any]:
    story = [Paragraph(title, styles["SubHeader"])]
    data = [[
        paragraph("Entity", styles["TableHeader"]),
        paragraph("Role / Link", styles["TableHeader"]),
        paragraph("Period", styles["TableHeader"]),
        paragraph("Relevance", styles["TableHeader"]),
    ]]
    if rows:
        for r in rows:
            data.append([
                paragraph(r.get("name"), styles["SmallBody"]),
                paragraph(r.get("role"), styles["SmallBody"]),
                paragraph(r.get("period"), styles["SmallBody"]),
                paragraph(r.get("note"), styles["SmallBody"]),
            ])
    else:
        data.append([
            paragraph("Data not available", styles["SmallBody"]),
            paragraph("Data not available", styles["SmallBody"]),
            paragraph("Data not available", styles["SmallBody"]),
            paragraph("Data not available", styles["SmallBody"]),
        ])
    table = Table(data, colWidths=[1.55 * inch, 1.65 * inch, 0.9 * inch, 2.45 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eceff3")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#aeb5bd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.12 * inch))
    return story


def make_master_table(articles: List[Dict[str, Any]], styles) -> Table:
    headers = ["ID", "Date", "Source", "Headline / Title", "URL", "Summary", "Category", "Confidence", "Source Type"]
    data = [[paragraph(h, styles["TableHeader"]) for h in headers]]

    for a in articles:
        url = clean_text(a.get("url"))
        if url != "Data not available":
            url_cell = Paragraph(f'<link href="{url}">Open Link</link>', styles["SmallBody"])
        else:
            url_cell = paragraph("Data not available", styles["SmallBody"])

        data.append([
            paragraph(a.get("id"), styles["SmallBody"]),
            paragraph(a.get("date"), styles["SmallBody"]),
            paragraph(a.get("source"), styles["SmallBody"]),
            paragraph(a.get("headline"), styles["SmallBody"]),
            url_cell,
            paragraph(a.get("summary"), styles["SmallBody"]),
            paragraph(a.get("category"), styles["SmallBody"]),
            paragraph(a.get("confidence"), styles["SmallBody"]),
            paragraph(a.get("sourceType"), styles["SmallBody"]),
        ])

    col_widths = [
        0.35 * inch,
        0.65 * inch,
        0.75 * inch,
        1.35 * inch,
        0.65 * inch,
        1.35 * inch,
        0.78 * inch,
        0.62 * inch,
        0.8 * inch
    ]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8ecef")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b4bcc4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (4, 1), (4, -1), "CENTER"),
        ("ALIGN", (7, 1), (7, -1), "CENTER"),
    ]))
    return table


# =========================================================
# PDF BUILD
# =========================================================
def build_pdf_to_buffer(summary: Dict[str, Any], report_json: Dict[str, Any], sentiment_data: Dict[str, Any]) -> bytes:
    styles = build_styles()
    buffer = io.BytesIO()

    doc = ArchiveBufferDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    sections = report_json.get("sections", {})
    story: List[Any] = []

    title = report_json.get("title") or f"{summary['subject_name']} - Comprehensive Media Archive & Strategic Profile "
    story.append(Paragraph(title.replace("&", "&amp;"), styles["ReportTitle"]))

    story.append(Paragraph("Executive Summary", styles["SectionHeader"]))
    story.append(Paragraph(clean_text(sections.get("executive_summary")), styles["Body"]))
    for item in sections.get("executive_takeaways", []):
        story.append(Paragraph(f"• {clean_text(item)}", styles["BulletBody"]))

    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph("Media Coverage Overview", styles["SectionHeader"]))
    story.append(Paragraph(clean_text(sections.get("media_coverage_overview")), styles["Body"]))
    story.append(Paragraph(clean_text(sections.get("media_coverage_key_insight")), styles["Body"]))

    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph("Peak Coverage & Event Clusters", styles["SectionHeader"]))
    peak_rows = sections.get("peak_coverage_analysis", []) or [{"label": "Data not available", "explanation": "Data not available"}]
    story.append(make_peak_table(peak_rows, styles))
    story.append(Spacer(1, 0.06 * inch))
    story.append(Paragraph(clean_text(sections.get("peak_coverage_key_insight")), styles["Body"]))

    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph("Master Chronological Table", styles["SectionHeader"]))
    story.append(make_master_table(summary["articles"], styles))

    story.append(PageBreak())
    story.append(Paragraph("Decade Breakdown", styles["SectionHeader"]))
    decade_breakdown = sections.get("decade_breakdown", []) or []
    if decade_breakdown:
        for block in decade_breakdown:
            story.append(Paragraph(clean_text(block.get("period")), styles["SubHeader"]))
            story.append(Paragraph(clean_text(block.get("summary")), styles["Body"]))
    else:
        story.append(Paragraph("Data not available", styles["Body"]))

    story.append(Paragraph("Thematic Analysis", styles["SectionHeader"]))
    story.append(Paragraph(clean_text(sections.get("thematic_analysis")), styles["Body"]))
    story.append(Paragraph(clean_text(sections.get("thematic_key_insight")), styles["Body"]))

    story.append(Paragraph("Entity Mapping", styles["SectionHeader"]))
    story.append(Paragraph(clean_text(sections.get("entity_mapping_summary")), styles["Body"]))
    story.extend(make_entity_table("7.1 Business Entities", summary["entity_map"].get("business", []), styles))
    story.extend(make_entity_table("7.2 Advocacy / Community", summary["entity_map"].get("advocacy", []), styles))
    story.extend(make_entity_table("7.3 Political / Affiliations", summary["entity_map"].get("politics", []), styles))
    story.extend(make_entity_table("7.4 Government Roles", summary["entity_map"].get("government", []), styles))
    story.extend(make_entity_table("7.5 Media Presence", summary["entity_map"].get("media", []), styles))
    story.extend(make_entity_table("7.6 Awards / Recognition", summary["entity_map"].get("awards", []), styles))

    story.append(Paragraph("Methodology Note", styles["SectionHeader"]))
    story.append(Paragraph(clean_text(sections.get("methodology_note")), styles["Body"]))

    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph("Media Sentiment Breakdown", styles["SectionHeader"]))

    breakdown = sentiment_data.get("breakdown", {})
    sentiment_table = Table([[
        paragraph(f"POSITIVE: {breakdown.get('positive', 0)}%", styles["SubHeader"]),
        paragraph(f"NEGATIVE: {breakdown.get('negative', 0)}%", styles["SubHeader"]),
        paragraph(f"NEUTRAL: {breakdown.get('neutral', 0)}%", styles["SubHeader"]),
    ]], colWidths=[2.2 * inch, 2.2 * inch, 2.2 * inch])

    sentiment_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef1f4")),
        ("BOX", (0, 0), (-1, -1), 0.3, colors.HexColor("#c6ccd2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(sentiment_table)

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Peak Sentiment Events", styles["SectionHeader"]))

    peak_positive = sentiment_data.get("peak_positive")
    peak_negative = sentiment_data.get("peak_negative")

    if peak_positive:
        story.append(Paragraph(
            f'<font color="#119c46"><b>PEAK POSITIVE: {clean_text(peak_positive.get("sentiment_score"))}</b></font>',
            styles["Body"]
        ))
        story.append(Paragraph(
            f'{clean_text(peak_positive.get("date"))} — {clean_text(peak_positive.get("summary"))}',
            styles["Body"]
        ))
        story.append(Paragraph(
            f'Reason: {clean_text(peak_positive.get("sentiment_reason"))}',
            styles["SmallBody"]
        ))
    else:
        story.append(Paragraph("PEAK POSITIVE: Data not available", styles["Body"]))

    story.append(Spacer(1, 0.08 * inch))

    if peak_negative:
        story.append(Paragraph(
            f'<font color="#d62828"><b>PEAK NEGATIVE: {clean_text(peak_negative.get("sentiment_score"))}</b></font>',
            styles["Body"]
        ))
        story.append(Paragraph(
            f'{clean_text(peak_negative.get("date"))} — {clean_text(peak_negative.get("summary"))}',
            styles["Body"]
        ))
        story.append(Paragraph(
            f'Reason: {clean_text(peak_negative.get("sentiment_reason"))}',
            styles["SmallBody"]
        ))
    else:
        story.append(Paragraph("PEAK NEGATIVE: Data not available", styles["Body"]))

    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Closing Assessment", styles["SectionHeader"]))
    story.append(Paragraph(clean_text(sections.get("closing_assessment")), styles["Body"]))
    for q in sections.get("due_diligence_questions", []):
        story.append(Paragraph(f"• {clean_text(q)}", styles["BulletBody"]))
    story.append(Paragraph(clean_text(sections.get("closing_key_insight")), styles["Body"]))

    story.append(Paragraph("End of Report", styles["SubHeader"]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# =========================================================
# PUBLIC API FOR FASTAPI ROUTE
# =========================================================
def generate_pdf_bytes(subject: str) -> bytes:
    mongo_doc = load_document_from_mongodb(subject)
    summary = build_dataset_summary(mongo_doc, subject)
    report_json = generate_report_json_with_gemini(summary)
    sentiment_data = extract_sentiment_from_dashboard(mongo_doc)
    return build_pdf_to_buffer(summary, report_json, sentiment_data)