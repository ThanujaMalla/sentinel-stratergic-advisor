from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IntelligenceRecord(BaseModel):
    source: str
    source_type: str
    title: str
    url: str | None = None
    published_at: str | None = None
    content: str | None = None
    author: str | None = None
    language: str | None = None
    region: str | None = None
    person_query: str

    category: str | None = None
    sentiment: str | None = None
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    confidence: str | float | None = None

    raw: dict[str, Any] = Field(default_factory=dict)
    normalized_name: str
