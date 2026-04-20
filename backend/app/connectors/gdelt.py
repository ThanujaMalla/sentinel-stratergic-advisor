from __future__ import annotations

from urllib.parse import quote

import httpx

from app.utils.helpers import normalize_text


async def fetch_gdelt(name: str, max_records: int = 25) -> dict:
    try:
        encoded_name = quote(name.strip())
        url = (
            'https://api.gdeltproject.org/api/v2/doc/doc'
            f'?query={encoded_name}&mode=ArtList&format=json&maxrecords={max_records}'
        )

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)

        if resp.status_code != 200:
            return {'source': 'GDELT', 'ok': False, 'items': [], 'error': f'HTTP {resp.status_code}: {resp.text[:300]}'}

        data = resp.json()
        articles = data.get('articles', [])
        items = []
        for article in articles:
            title = normalize_text(article.get('title'))
            domain = normalize_text(article.get('domain'))
            article_url = article.get('url')
            items.append(
                {
                    'title': title or f'GDELT result for {name}',
                    'url': article_url,
                    'content': normalize_text(title or domain or article_url or ''),
                    'published_at': article.get('seendate'),
                    'author': domain,
                    'language': article.get('language'),
                    'region': 'global',
                    'raw': article,
                }
            )
        return {'source': 'GDELT', 'ok': True, 'items': items, 'error': ''}
    except Exception as exc:
        return {'source': 'GDELT', 'ok': False, 'items': [], 'error': repr(exc)}
