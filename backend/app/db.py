from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection

from app.config import settings


if not settings.MONGODB_URI:
    raise RuntimeError('MONGODB_URI is missing in backend .env')

mongo_client = MongoClient(settings.MONGODB_URI)
mongo_db = mongo_client[settings.MONGODB_DB]
intelligence_collection: Collection = mongo_db[settings.MONGODB_COLLECTION]
profile_collection: Collection = mongo_db[settings.MONGODB_PROFILE_COLLECTION]
counter_collection: Collection = mongo_db['counters']


def slugify_name(name: str) -> str:
    value = re.sub(r'[^a-zA-Z0-9]+', '_', name.strip().lower())
    return value.strip('_')


def create_indexes() -> None:
    intelligence_collection.create_index('person_id', unique=True)
    intelligence_collection.create_index('person_name')
    intelligence_collection.create_index('person_key', unique=True)
    profile_collection.create_index('id', unique=True)


def _get_next_person_id() -> int:
    counter = counter_collection.find_one_and_update(
        {'_id': 'person_id'},
        {'$inc': {'sequence_value': 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(counter['sequence_value'])


def save_profile(profile_id: str, name: str, data: Any) -> None:
    profile_collection.update_one(
        {'id': profile_id},
        {
            '$set': {
                'id': profile_id,
                'name': name,
                'data': data,
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
        },
        upsert=True,
    )


def get_profile(profile_id: str) -> Any | None:
    item = profile_collection.find_one({'id': profile_id}, {'_id': 0, 'data': 1})
    return item.get('data') if item else None


def list_profiles() -> list[dict[str, Any]]:
    profiles = list(
        profile_collection.find({}, {'_id': 0, 'id': 1, 'name': 1, 'created_at': 1}).sort('created_at', -1)
    )
    return profiles


def get_person_document(person_name: str) -> dict[str, Any] | None:
    person_key = slugify_name(person_name)
    return intelligence_collection.find_one({'person_key': person_key}, {'_id': 0, 'person_key': 0})

def save_person_intelligence(
    person_name: str,
    fetched_payload: dict[str, Any],
    dashboard_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    person_key = slugify_name(person_name)
    existing = intelligence_collection.find_one({"person_key": person_key}, {"_id": 0, "person_id": 1})
    person_id = existing["person_id"] if existing else _get_next_person_id()

    document: dict[str, Any] = {
        "person_id": person_id,
        "person_name": person_name,
        "person_key": person_key,
        "fetched_data": fetched_payload,
        "articles": fetched_payload.get("articles", []),
    }

    if dashboard_data is not None:
        document["dashboard_data"] = dashboard_data

    intelligence_collection.update_one({"person_key": person_key}, {"$set": document}, upsert=True)
    saved = intelligence_collection.find_one({"person_key": person_key}, {"_id": 0, "person_key": 0})
    return saved or document