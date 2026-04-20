from __future__ import annotations

import httpx

from app.config import settings
from app.utils.helpers import normalize_text


async def fetch_news_api(name: str, max_records: int = 10) -> dict:
    if not settings.NEWS_API_KEY:
        return {'source': 'NewsAPI', 'ok': False, 'items': [], 'error': 'NEWS_API_KEY missing'}

    url = 'https://newsapi.org/v2/everything'
    params = {
        'q': f'"{name}"',
        'language': 'en',
        'sortBy': 'publishedAt',
        'pageSize': max_records,
        'apiKey': settings.NEWS_API_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return {'source': 'NewsAPI', 'ok': False, 'items': [], 'error': resp.text[:300]}
        data = resp.json()
        articles = data.get('articles', [])
        items = []
        for article in articles:
            items.append(
                {
                    'title': article.get('title'),
                    'url': article.get('url'),
                    'content': normalize_text(article.get('description') or article.get('content')),
                    'published_at': article.get('publishedAt'),
                    'author': article.get('author'),
                    'language': 'en',
                    'region': 'global',
                    'raw': article,
                }
            )
        return {'source': 'NewsAPI', 'ok': True, 'items': items, 'error': ''}
    except Exception as exc:
        return {'source': 'NewsAPI', 'ok': False, 'items': [], 'error': repr(exc)}
