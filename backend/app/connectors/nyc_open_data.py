from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.utils.helpers import normalize_text

NYC_ROW_DATASETS = [
    {'name': 'City Council Meetings', 'dataset_id': 'm48u-yjt8', 'region': 'New York City'},
    {'name': 'City Clerk eLobbyist Data', 'dataset_id': 'fmf3-knd8', 'region': 'New York City'},
    {'name': 'CURRENT BASES', 'dataset_id': 'eccv-9dzr', 'region': 'New York City'},
    {'name': 'For-Hire Vehicles Active', 'dataset_id': '8wbx-tsch', 'region': 'New York City'},
]

LIKELY_SEARCHABLE_KEYWORDS = [
    'name', 'entity', 'candidate', 'contributor', 'lobby', 'client', 'subject', 'title',
    'description', 'person', 'owner', 'applicant', 'licensee', 'respondent', 'petitioner',
    'committee', 'body'
]


def _escape_soql_like(value: str) -> str:
    return value.replace("'", "''")


def _build_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    if settings.NYC_OPEN_DATA_APP_TOKEN:
        headers['X-App-Token'] = settings.NYC_OPEN_DATA_APP_TOKEN
    return headers


async def _fetch_dataset_metadata(client: httpx.AsyncClient, dataset_id: str) -> dict[str, Any]:
    resp = await client.get(f'{settings.NYC_OPEN_DATA_BASE_URL}/api/views/{dataset_id}.json')
    resp.raise_for_status()
    return resp.json()


def _pick_searchable_columns(metadata: dict[str, Any]) -> list[str]:
    columns = metadata.get('columns', []) or []
    chosen: list[str] = []
    for col in columns:
        field_name = (col.get('fieldName') or '').strip()
        name = (col.get('name') or '').strip().lower()
        desc = (col.get('description') or '').strip().lower()
        if not field_name:
            continue
        haystack = f'{field_name.lower()} {name} {desc}'
        if any(keyword in haystack for keyword in LIKELY_SEARCHABLE_KEYWORDS):
            chosen.append(field_name)
    deduped: list[str] = []
    seen: set[str] = set()
    for col in chosen:
        if col not in seen:
            seen.add(col)
            deduped.append(col)
    return deduped


def _build_where_clause(person_name: str, columns: list[str]) -> str:
    safe_name = _escape_soql_like(person_name.strip())
    return ' OR '.join([f"upper({col}) like upper('%{safe_name}%')" for col in columns])


async def _query_dataset_rows(client: httpx.AsyncClient, dataset_id: str, where_clause: str, limit: int) -> list[dict[str, Any]]:
    resp = await client.get(
        f'{settings.NYC_OPEN_DATA_BASE_URL}/resource/{dataset_id}.json',
        params={'$where': where_clause, '$limit': limit},
    )
    resp.raise_for_status()
    return resp.json()


async def fetch_nyc_open_data(person_name: str, max_records: int = 25) -> dict:
    try:
        items: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30, headers=_build_headers()) as client:
            for dataset in NYC_ROW_DATASETS:
                try:
                    metadata = await _fetch_dataset_metadata(client, dataset['dataset_id'])
                    searchable_columns = _pick_searchable_columns(metadata)
                    if not searchable_columns:
                        continue
                    rows = await _query_dataset_rows(
                        client,
                        dataset['dataset_id'],
                        _build_where_clause(person_name, searchable_columns),
                        max_records,
                    )
                    for row in rows:
                        items.append(
                            {
                                'title': f"{dataset['name']} record",
                                'url': f"{settings.NYC_OPEN_DATA_BASE_URL}/resource/{dataset['dataset_id']}.json",
                                'content': normalize_text(str(row)),
                                'published_at': None,
                                'author': 'NYC Open Data',
                                'language': 'en',
                                'region': dataset['region'],
                                'raw': {
                                    'dataset_id': dataset['dataset_id'],
                                    'dataset_name': dataset['name'],
                                    'matched_columns': searchable_columns,
                                    'row': row,
                                },
                            }
                        )
                except Exception:
                    continue
        return {'source': 'NYC Open Data', 'ok': True, 'items': items, 'error': ''}
    except Exception as exc:
        return {'source': 'NYC Open Data', 'ok': False, 'items': [], 'error': repr(exc)}
