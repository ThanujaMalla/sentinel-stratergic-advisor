from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db import (
    create_indexes,
    get_person_document,
    get_profile,
    list_profiles,
    save_person_intelligence,
    save_profile,
)
from app.services.gemini_service import fetch_broadcast_transcripts, fetch_drilldown_articles
from app.services.ingestion_service import fetch_all_sources
from app.services.intelligence_service import synthesize_intelligence
from app.services.pdf_service import generate_pdf_bytes

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_indexes()
    yield


app = FastAPI(title="Sentinel Strategic Advisor API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProfilePayload(BaseModel):
    id: str
    name: str
    data: Any


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/profiles")
async def profiles() -> list[dict[str, Any]]:
    return list_profiles()


@app.get("/api/profiles/{profile_id}")
async def profile_detail(profile_id: str) -> Any:
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.post("/api/profiles")
async def create_profile(payload: ProfilePayload) -> dict[str, bool]:
    save_profile(payload.id, payload.name, payload.data)
    return {"success": True}


@app.get("/api/search")
async def search(
    q: str = Query(..., min_length=1),
    refresh: bool = Query(False, description="Force fresh fetch instead of using MongoDB cache"),
) -> dict[str, Any]:
    try:
        existing = get_person_document(q)

        if existing and not refresh and existing.get("dashboard_data"):
            return existing["dashboard_data"]

        raw_data = existing.get("fetched_data") if existing and not refresh else None

        if not raw_data:
            raw_data = await fetch_all_sources(q)
            save_person_intelligence(
                q,
                raw_data,
                existing.get("dashboard_data") if existing else None,
            )

        dashboard_data = await synthesize_intelligence(q, raw_data)
        save_person_intelligence(q, raw_data, dashboard_data)
        return dashboard_data

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/drilldown")
async def drilldown(
    subject: str = Query(...),
    category: str = Query(...),
) -> list[dict[str, Any]]:
    try:
        return await fetch_drilldown_articles(subject, category)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/transcripts")
async def transcripts(
    subject: str = Query(...),
    query: str | None = Query(None),
) -> list[dict[str, Any]]:
    try:
        return await fetch_broadcast_transcripts(subject, query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/export/pdf")
async def export_pdf(subject: str = Query(..., min_length=1)):
    try:
        pdf_bytes = generate_pdf_bytes(subject)
        filename = f"{subject.replace(' ', '_')}_media_archive.pdf"

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc