from __future__ import annotations

import httpx

from app.utils.helpers import normalize_text


async def fetch_wikipedia(name: str) -> dict:
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{name.replace(' ', '%20')}"
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return {'source': 'Wikipedia', 'ok': False, 'items': [], 'error': 'Page not found'}
        data = resp.json()
        title = data.get('title', name)
        extract = normalize_text(data.get('extract'))
        page_url = data.get('content_urls', {}).get('desktop', {}).get('page')
        return {
            'source': 'Wikipedia',
            'ok': True,
            'items': [{
                'title': title,
                'url': page_url,
                'content': extract,
                'published_at': None,
                'author': 'Wikipedia',
                'language': 'en',
                'region': 'global',
                'raw': data,
            }],
            'summary': extract,
            'error': '',
        }
    except Exception as exc:
        return {'source': 'Wikipedia', 'ok': False, 'items': [], 'error': repr(exc)}
