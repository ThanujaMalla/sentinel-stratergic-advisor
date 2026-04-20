from __future__ import annotations

import asyncio
import html
import re
from typing import Any

from app.connectors.gdelt import fetch_gdelt
from app.connectors.google_news import fetch_google_news
from app.connectors.news_api import fetch_news_api
from app.connectors.nyc_open_data import fetch_nyc_open_data
from app.connectors.wikipedia import fetch_wikipedia
from app.services.gemini_service import (
    fetch_broadcast_transcripts,
    fetch_court_records,
    fetch_factiva,
    fetch_lexis_nexis,
    fetch_nyccfb,
    fetch_twitter,
    fetch_youtube,
)
from app.services.normalization_service import deduplicate_records, normalize_source_items


def clean_html_text(value: object) -> str:
    if value is None:
        return "Data not available"

    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "Data not available"


async def fetch_all_sources(person_name: str) -> dict[str, Any]:
    results = await asyncio.gather(
        fetch_wikipedia(person_name),
        fetch_gdelt(person_name, max_records=25),
        fetch_news_api(person_name, max_records=25),
        fetch_google_news(person_name, max_records=25),
        fetch_nyc_open_data(person_name, max_records=25),
        fetch_youtube(person_name),
        fetch_twitter(person_name),
        fetch_factiva(person_name),
        fetch_lexis_nexis(person_name),
        fetch_nyccfb(person_name),
        fetch_broadcast_transcripts(person_name),
        fetch_court_records(person_name),
        return_exceptions=True,
    )

    output: dict[str, Any] = {
        "name": person_name,
        "wikipedia": None,
        "sources": [],
        "errors": [],
        "news": [],
        "wiki": None,
        "youtube": [],
        "google_news": [],
        "tweets": [],
        "factiva": [],
        "lexis": [],
        "nyccfb": [],
        "courtMeta": {},
        "transcripts": [],
    }

    all_records = []

    source_mapping = [
        ("Wikipedia", "knowledge"),
        ("GDELT", "news"),
        ("NewsAPI", "news"),
        ("Google News", "news"),
        ("NYC Open Data", "government"),
    ]

    for idx, result in enumerate(results[:5]):
        if isinstance(result, Exception):
            output["errors"].append(str(result))
            continue

        source, source_type = source_mapping[idx]
        items = result.get("items", [])
        ok = result.get("ok", True)
        error = result.get("error", "")

        if not ok:
            output["errors"].append(f'{source}: {error or "Unknown source failure"}')
            output["sources"].append({"source": source, "count": 0, "ok": False})
            continue

        if source == "Wikipedia":
            output["wikipedia"] = result.get("summary")
            output["wiki"] = {
                "title": items[0].get("title") if items else person_name,
                "extract": result.get("summary"),
                "url": items[0].get("url") if items else None,
            } if items else None

        if source == "Google News":
            output["google_news"] = items

        normalized = normalize_source_items(person_name, source, source_type, items)
        all_records.extend(normalized)
        output["sources"].append({"source": source, "count": len(items), "ok": True})

    youtube_result = results[5]
    if isinstance(youtube_result, Exception):
        output["errors"].append(f"YouTube: {str(youtube_result)}")
        output["youtube"] = []
        output["sources"].append({"source": "YouTube", "count": 0, "ok": False})
    else:
        output["youtube"] = youtube_result or []
        youtube_items = [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "content": item.get("title"),
                "published_at": item.get("date"),
                "author": item.get("channel"),
                "language": "en",
                "region": "global",
                "raw": item,
            }
            for item in output["youtube"]
        ]
        normalized_youtube = normalize_source_items(person_name, "YouTube", "video", youtube_items)
        all_records.extend(normalized_youtube)
        output["sources"].append({"source": "YouTube", "count": len(output["youtube"]), "ok": True})

    output["tweets"] = results[6] if not isinstance(results[6], Exception) else []
    output["factiva"] = results[7] if not isinstance(results[7], Exception) else []
    output["lexis"] = results[8] if not isinstance(results[8], Exception) else []
    output["nyccfb"] = results[9] if not isinstance(results[9], Exception) else []
    output["transcripts"] = results[10] if not isinstance(results[10], Exception) else []
    output["courtMeta"] = results[11] if not isinstance(results[11], Exception) else {}

    for label, payload in [
        ("Twitter", output["tweets"]),
        ("Factiva", output["factiva"]),
        ("LexisNexis", output["lexis"]),
        ("NYCCFB", output["nyccfb"]),
        ("Transcripts", output["transcripts"]),
    ]:
        output["sources"].append({
            "source": label,
            "count": len(payload) if isinstance(payload, list) else 0,
            "ok": True,
        })

    deduped = deduplicate_records(all_records)

    output["records"] = [r.model_dump() for r in deduped]
    output["articles"] = [
    {
        "id": index,
        "date": clean_html_text(record.published_at),
        "headline": clean_html_text(record.title),
        "url": clean_html_text(record.url),
        "summary": clean_html_text(record.content),
        "category": record.category or "Other",
        "confidence": "RECALLED",
        "source": clean_html_text(record.author if record.source == "Google News" and record.author else record.source),
        "sourceType": clean_html_text(record.source_type),
    }
    for index, record in enumerate(deduped, start=1)
]
    return output