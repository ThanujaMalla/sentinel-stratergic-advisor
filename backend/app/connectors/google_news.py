from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, quote, unquote, urlparse

import httpx

from app.utils.helpers import normalize_text


def clean_html_text(value: object) -> str:
    if value is None:
        return ""

    text = html.unescape(str(value))
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>|</div>|</li>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_real_url(google_link: str | None) -> str | None:
    if not google_link:
        return None

    try:
        parsed = urlparse(google_link)
        qs = parse_qs(parsed.query)

        for key in ("url", "q", "u"):
            if key in qs and qs[key]:
                return unquote(qs[key][0])

        return google_link
    except Exception:
        return google_link


def extract_source_from_description(description: str) -> str:
    text = clean_html_text(description)

    if " - " in text:
        parts = text.rsplit(" - ", 1)
        if len(parts) == 2 and len(parts[1].strip()) <= 80:
            return normalize_text(parts[1]) or "Google News"

    return "Google News"


def build_google_news_summary(title: str, description: str) -> str:
    clean_title = clean_html_text(title)
    clean_desc = clean_html_text(description)

    if clean_desc.lower().startswith(clean_title.lower()):
        clean_desc = clean_desc[len(clean_title):].strip(" -:|")

    if " - " in clean_desc:
        main_part, tail = clean_desc.rsplit(" - ", 1)
        if len(tail.strip()) <= 80:
            clean_desc = main_part.strip()

    clean_desc = re.sub(r"View Full Coverage|Read more", "", clean_desc, flags=re.IGNORECASE).strip()
    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

    return normalize_text(clean_desc or clean_title)


async def fetch_google_news(name: str, max_records: int = 25) -> dict:
    try:
        query = quote(name.strip())
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)

        if resp.status_code != 200:
            return {
                "source": "Google News",
                "ok": False,
                "items": [],
                "error": f"HTTP {resp.status_code}: {resp.text[:300]}",
            }

        root = ET.fromstring(resp.text)
        items = []

        for idx, item in enumerate(root.findall("./channel/item"), start=1):
            if idx > max_records:
                break

            title = item.findtext("title")
            link = item.findtext("link")
            pub_date = item.findtext("pubDate")
            description = item.findtext("description")

            cleaned_title = normalize_text(clean_html_text(title)) or f"Google News result for {name}"
            cleaned_summary = build_google_news_summary(cleaned_title, description or "")
            real_url = extract_real_url(link)
            source_name = extract_source_from_description(description or "")

            items.append(
                {
                    "title": cleaned_title,
                    "url": real_url,
                    "content": cleaned_summary,
                    "published_at": pub_date,
                    "author": source_name,
                    "language": "en",
                    "region": "global",
                    "raw": {
                        "google_news_link": link,
                        "description": description,
                        "title": title,
                        "pubDate": pub_date,
                    },
                }
            )

        return {
            "source": "Google News",
            "ok": True,
            "items": items,
            "error": "",
        }

    except Exception as exc:
        return {
            "source": "Google News",
            "ok": False,
            "items": [],
            "error": repr(exc),
        }