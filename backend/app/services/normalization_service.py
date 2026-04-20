from __future__ import annotations

from app.models.schemas import IntelligenceRecord
from app.services.gemini_service import classify_texts_fast
from app.utils.helpers import normalize_text, stable_hash

def classify_source_type(source_name: str, source_type: str, url: str | None, content: str | None) -> str:
    s = (source_name or "").lower()
    u = (url or "").lower()
    c = (content or "").lower()

    # -------------------------
    # PRIMARY (official/legal/gov)
    # -------------------------
    if any(k in s or k in u for k in [
        ".gov", "court", "legal", "sec.gov", "justice", "nyc.gov",
        "federal", "regulator", "filing", "official"
    ]):
        return "Primary"

    # -------------------------
    # SECONDARY / BIOGRAPHICAL
    # -------------------------
    if any(k in s or k in u for k in [
        "wikipedia", "britannica", "biography", "profile"
    ]):
        return "Secondary/biographical"

    if any(k in c for k in [
        "who is", "biography", "profile", "facts", "early life", "net worth"
    ]):
        return "Secondary/biographical"

    # -------------------------
    # SECONDARY RECALL (weak sources)
    # -------------------------
    if any(k in s or u for k in [
        "blog", "medium.com", "substack", "opinion", "editorial"
    ]):
        return "Secondary recall"

    if any(k in c for k in [
        "opinion", "analysis", "retrospective", "review"
    ]):
        return "Secondary recall"

    # -------------------------
    # DEFAULT → SECONDARY (news)
    # -------------------------
    return "Secondary"

def normalize_source_items(
    person_name: str,
    source_name: str,
    source_type: str,
    items: list,
) -> list[IntelligenceRecord]:
    prepared = []

    for item in items:
        title = normalize_text(item.get("title")) or f"{person_name} - untitled"
        content = normalize_text(item.get("content"))
        url = item.get("url")
        published_at = item.get("published_at")
        author = item.get("author")
        language = item.get("language")
        region = item.get("region")
        raw = item.get("raw", {})

        normalized_name = stable_hash(
            f"{person_name}|{source_name}|{title}|{url or ''}|{(content or '')[:250]}"
        )

        classify_text = " ".join([
            title or "",
            content or "",
        ]).strip()

        prepared.append({
            "title": title,
            "content": content,
            "url": url,
            "published_at": published_at,
            "author": author,
            "language": language,
            "region": region,
            "raw": raw,
            "normalized_name": normalized_name,
            "classify_text": classify_text,
        })

    categories = classify_texts_fast([p["classify_text"] for p in prepared])

    records: list[IntelligenceRecord] = []
    for item, category in zip(prepared, categories):
        classified_source_type = classify_source_type(
        source_name=source_name,
        source_type=source_type,
        url=url,
        content=content
    )

        record = IntelligenceRecord(
            source=source_name,
            source_type=classified_source_type,
                title=item["title"],
                url=item["url"],
                published_at=item["published_at"],
                content=item["content"],
                author=item["author"],
                language=item["language"],
                region=item["region"],
                person_query=person_name,
                category=category,
                raw=item["raw"],
                normalized_name=item["normalized_name"],
            )
        records.append(record)

    return records


def deduplicate_records(records: list[IntelligenceRecord]) -> list[IntelligenceRecord]:
    unique: list[IntelligenceRecord] = []
    seen: set[str] = set()

    for record in records:
        content_preview = (record.content or "")[:250]
        key = stable_hash(
            f"{record.source}|{record.title}|{record.url}|{content_preview}"
        )

        if key not in seen:
            seen.add(key)
            unique.append(record)

    return unique