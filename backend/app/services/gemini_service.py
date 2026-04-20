from __future__ import annotations

import asyncio
import os
from typing import Any
from urllib.parse import quote
import re
import google.generativeai as genai
import httpx

NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')
TWITTER_BEARER = os.getenv('TWITTER_BEARER', '')
FACTIVA_API_KEY = os.getenv('FACTIVA_API_KEY', '')
LEXISNEXIS_API_KEY = os.getenv('LEXISNEXIS_API_KEY', '')
TIMEOUT = httpx.Timeout(30.0, connect=15.0)


async def fetch_factiva(query: str) -> list[dict[str, Any]]:
    if not FACTIVA_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                'https://api.dowjones.com/alpha/search',
                headers={'Content-Type': 'application/json', 'X-API-KEY': FACTIVA_API_KEY},
                json={'query': {'search_string': query, 'date_range': 'last_10_years'}, 'formatting': 'json'},
            )
            r.raise_for_status()
            data = r.json()
        return [
            {
                'title': i.get('attributes', {}).get('title'),
                'source': i.get('attributes', {}).get('source_name'),
                'date': i.get('attributes', {}).get('publication_date'),
                'snippet': i.get('attributes', {}).get('snippet'),
            }
            for i in data.get('data', [])
        ]
    except Exception:
        return []


async def fetch_lexis_nexis(query: str) -> list[dict[str, Any]]:
    if not LEXISNEXIS_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f'https://api.lexisnexis.com/v1/search?q={quote(query)}',
                headers={'Accept': 'application/json', 'Authorization': f'Bearer {LEXISNEXIS_API_KEY}'},
            )
            r.raise_for_status()
            data = r.json()
        out = []
        for item in data.get('value', []):
            source_title = item.get('SourceTitle')
            sl = (source_title or '').lower()
            out.append(
                {
                    'title': item.get('Title'),
                    'source': source_title,
                    'date': item.get('PublicationDate'),
                    'url': item.get('WebLink'),
                    'isTranscript': any(k in sl for k in ['transcript', 'cnn', 'fox', 'msnbc']),
                }
            )
        return out
    except Exception:
        return []


async def fetch_broadcast_transcripts(name: str, custom_query: str | None = None) -> list[dict[str, Any]]:
    if not LEXISNEXIS_API_KEY:
        return []
    query = custom_query or f'"{name}" AND (source(CNN) OR source(Fox News) OR source(MSNBC)) AND (transcript OR broadcast)'
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f'https://api.lexisnexis.com/v1/search?q={quote(query)}',
                headers={'Accept': 'application/json', 'Authorization': f'Bearer {LEXISNEXIS_API_KEY}'},
            )
            r.raise_for_status()
            data = r.json()
        return [
            {
                'title': item.get('Title'),
                'network': item.get('SourceTitle'),
                'date': item.get('PublicationDate'),
                'url': item.get('WebLink'),
                'snippet': item.get('Snippet'),
            }
            for item in data.get('value', [])
        ]
    except Exception:
        return []


async def fetch_news_api(query: str) -> list[dict[str, Any]]:
    if not NEWS_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                'https://newsapi.org/v2/everything',
                params={'q': query, 'sortBy': 'relevancy', 'pageSize': 10, 'apiKey': NEWS_API_KEY},
            )
            r.raise_for_status()
            data = r.json()
        return [
            {
                'title': a.get('title'),
                'source': (a.get('source') or {}).get('name'),
                'date': a.get('publishedAt'),
                'url': a.get('url'),
                'summary': a.get('description'),
            }
            for a in data.get('articles', [])
        ]
    except Exception:
        return []


async def fetch_wikipedia(query: str) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f'https://en.wikipedia.org/api/rest_v1/page/summary/{quote(query)}')
            if r.status_code >= 400:
                return None
            data = r.json()
        return {
            'title': data.get('title'),
            'extract': data.get('extract'),
            'url': ((data.get('content_urls') or {}).get('desktop') or {}).get('page'),
        }
    except Exception:
        return None


async def fetch_youtube(query: str) -> list[dict[str, Any]]:
    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY missing")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 5,
                "key": YOUTUBE_API_KEY,
            },
        )
        r.raise_for_status()
        data = r.json()

    return [
        {
            "title": i.get("snippet", {}).get("title"),
            "channel": i.get("snippet", {}).get("channelTitle"),
            "date": i.get("snippet", {}).get("publishedAt"),
            "url": f"https://www.youtube.com/watch?v={i.get('id', {}).get('videoId', '')}",
        }
        for i in data.get("items", [])
    ]

async def fetch_twitter(query: str) -> list[dict[str, Any]]:
    if not TWITTER_BEARER:
        return []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                'https://api.twitter.com/2/tweets/search/recent',
                params={'query': query, 'max_results': 10},
                headers={'Authorization': f'Bearer {TWITTER_BEARER}'},
            )
            r.raise_for_status()
            data = r.json()
        return [
            {
                'text': t.get('text'),
                'id': t.get('id'),
                'url': f"https://twitter.com/i/web/status/{t.get('id', '')}",
            }
            for t in data.get('data', [])
        ]
    except Exception:
        return []


async def fetch_nyccfb(name: str) -> list[dict[str, Any]]:
    try:
        parts = name.split()
        first = parts[0] if parts else name
        last = parts[-1] if len(parts) > 1 else ''
        search_name = f'{last}, {first}'.upper() if last else name.upper()
        url = f"https://data.cityofnewyork.us/resource/8686-7u7x.json?$where=name like '%{quote(search_name)}%'&$limit=50"
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
        return [
            {
                'year': i.get('election'),
                'recipient': i.get('candid'),
                'amount': i.get('amout'),
                'date': i.get('date'),
                'purpose': i.get('purpose'),
            }
            for i in data
        ]
    except Exception:
        return []


async def fetch_court_records(name: str) -> dict[str, Any]:
    return {
        'pacerQuery': f'site:pacer.gov "{name}"',
        'nyscefQuery': f'site:iapps.courts.state.ny.us "{name}"',
        'nysftdQuery': 'site:iapps.courts.state.ny.us "New York State Federation of Taxi Drivers"',
        'generalLitigationQuery': f'"{name}" lawsuit OR litigation OR court record',
    }


async def fetch_raw_intelligence(name: str) -> dict[str, Any]:
    news, wiki, youtube, tweets, factiva, lexis, nyccfb, court_meta, transcripts = await asyncio.gather(
        fetch_news_api(name),
        fetch_wikipedia(name),
        fetch_youtube(name),
        fetch_twitter(name),
        fetch_factiva(name),
        fetch_lexis_nexis(name),
        fetch_nyccfb(name),
        fetch_court_records(name),
        fetch_broadcast_transcripts(name),
    )
    return {
        'name': name,
        'news': news,
        'wiki': wiki,
        'youtube': youtube,
        'tweets': tweets,
        'factiva': factiva,
        'lexis': lexis,
        'nyccfb': nyccfb,
        'courtMeta': court_meta,
        'transcripts': transcripts,
    }


async def fetch_drilldown_articles(subject: str, category: str) -> list[dict[str, Any]]:
    q = f'{subject} {category}'
    news, factiva, lexis = await asyncio.gather(fetch_news_api(q), fetch_factiva(q), fetch_lexis_nexis(q))
    return sorted([*(news or []), *(factiva or []), *(lexis or [])], key=lambda x: x.get('date') or '', reverse=True)

import os
import re
import json
import hashlib
from typing import List, Dict

import google.generativeai as genai

_CATEGORY_CACHE: Dict[str, str] = {}

ALLOWED_CATEGORIES = [
    "Community activism",
    "Awards / recognition",
    "TV / broadcast",
    "Legal / litigation",
    "Business activity",
    "Political activity",
    "Media coverage",
    "Crime / investigation",
    "Personal profile",
    "Other",
]


def _cache_key(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()

def classify_category_rule_based(text: str) -> str | None:
    t = (text or "").lower().strip()

    if not t:
        return "Other"

    legal_keywords = [
        "sued", "lawsuit", "legal", "court", "judge", "litigation",
        "complaint", "trial", "settlement", "hearing", "regulator", "regulatory",
        "naacp sues", "probe", "petition"
    ]
    political_keywords = [
        "senator", "president", "government", "election", "campaign",
        "democrat", "republican", "governor", "mayor", "midterms",
        "trump", "political", "congress", "white house", "policy"
    ]
    business_keywords = [
        "tesla", "spacex", "xai", "investment", "profit", "market",
        "suppliers", "chip", "factory", "business", "company", "stocks",
        "payments", "paypal", "portfolio", "venture capital", "vc",
        "funding", "valuation", "manufacturing", "revenue", "earnings"
    ]
    media_keywords = [
        "analysis", "interview", "opinion", "review", "reported",
        "coverage", "feature", "news report", "editorial", "article"
    ]
    tv_keywords = [
        "tv", "television", "broadcast", "cnn", "fox news", "msnbc",
        "youtube", "channel", "podcast", "on air", "streaming", "episode"
    ]
    crime_keywords = [
        "crime", "investigation", "fraud", "police", "arrest", "scam",
        "accused", "charged", "criminal", "fbi"
    ]
    award_keywords = [
        "award", "awards", "recognition", "honor", "honoured", "recipient", "prize"
    ]
    activism_keywords = [
        "community", "activism", "activist", "protest", "nonprofit",
        "charity", "advocacy", "campaigners", "grassroots"
    ]
    profile_keywords = [
        "who is", "biography", "facts", "profile", "explained", "britannica",
        "quote of the day", "net worth", "age", "life story"
    ]

    if any(k in t for k in legal_keywords):
        return "Legal / litigation"
    if any(k in t for k in political_keywords):
        return "Political activity"
    if any(k in t for k in business_keywords):
        return "Business activity"
    if any(k in t for k in tv_keywords):
        return "TV / broadcast"
    if any(k in t for k in crime_keywords):
        return "Crime / investigation"
    if any(k in t for k in award_keywords):
        return "Awards / recognition"
    if any(k in t for k in activism_keywords):
        return "Community activism"
    if any(k in t for k in profile_keywords):
        return "Personal profile"
    if any(k in t for k in media_keywords):
        return "Media coverage"

    # nearest fallback instead of Other
    return "Media coverage"

def classify_categories_batch_with_gemini(texts: List[str]) -> List[str]:
    if not texts:
        return []

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return [classify_category_rule_based(t) or "Media coverage" for t in texts]

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3-flash-preview")

        prompt = f"""
You are a strict news-category classifier.

TASK:
Classify each input item into EXACTLY ONE nearest category.

Allowed categories:
- Community activism
- Awards / recognition
- TV / broadcast
- Legal / litigation
- Business activity
- Political activity
- Media coverage
- Crime / investigation
- Personal profile
- Other

IMPORTANT:
- Choose the CLOSEST matching category.
- Do NOT return "Other" for normal news/articles/posts/videos.
- Return "Other" ONLY if the text is empty, meaningless, or completely unrelated.
- Preserve input order.
- Return VALID JSON only.
- Output must be a JSON array of category strings.

INPUTS:
{json.dumps(texts, ensure_ascii=False, indent=2)}
""".strip()

        res = model.generate_content(prompt)
        raw = (res.text or "").strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"^```\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            return [classify_category_rule_based(t) or "Media coverage" for t in texts]

        cleaned: List[str] = []
        for i, item in enumerate(parsed[:len(texts)]):
            item_str = str(item).strip()

            exact = next((cat for cat in ALLOWED_CATEGORIES if item_str.lower() == cat.lower()), None)
            if exact:
                # avoid weak Other for real content
                if exact == "Other" and texts[i].strip():
                    cleaned.append(classify_category_rule_based(texts[i]) or "Media coverage")
                else:
                    cleaned.append(exact)
                continue

            partial = next((cat for cat in ALLOWED_CATEGORIES if cat.lower() in item_str.lower()), None)
            if partial:
                if partial == "Other" and texts[i].strip():
                    cleaned.append(classify_category_rule_based(texts[i]) or "Media coverage")
                else:
                    cleaned.append(partial)
                continue

            cleaned.append(classify_category_rule_based(texts[i]) or "Media coverage")

        while len(cleaned) < len(texts):
            cleaned.append("Media coverage")

        return cleaned

    except Exception:
        return [classify_category_rule_based(t) or "Media coverage" for t in texts]

def classify_texts_fast(texts: List[str]) -> List[str]:
    results: List[str] = ["Media coverage"] * len(texts)
    unresolved_indices: List[int] = []
    unresolved_texts: List[str] = []

    for idx, text in enumerate(texts):
        key = _cache_key(text)
        if key in _CATEGORY_CACHE:
            results[idx] = _CATEGORY_CACHE[key]
            continue

        rule_category = classify_category_rule_based(text)
        if rule_category is not None:
            results[idx] = rule_category
            _CATEGORY_CACHE[key] = rule_category
        else:
            unresolved_indices.append(idx)
            unresolved_texts.append(text)

    if unresolved_texts:
        llm_results = classify_categories_batch_with_gemini(unresolved_texts)
        for idx, category in zip(unresolved_indices, llm_results):
            results[idx] = category
            _CATEGORY_CACHE[_cache_key(texts[idx])] = category

    return results  