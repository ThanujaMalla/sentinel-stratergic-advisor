from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MATEO_ARCHIVE = json.loads((DATA_DIR / "mateo_archive.json").read_text(encoding="utf-8"))


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing in backend .env")
    return genai.Client(api_key=api_key)


def _dashboard_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "eventCount": {"type": "number"},
            "netSentiment": {"type": "string"},
            "totalFundraising": {"type": "string"},
            "electoralResult": {"type": "string"},
            "phases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "years": {"type": "string"},
                        "score": {"type": "string"},
                        "scoreClass": {"type": "string"},
                        "color": {"type": "string"},
                        "sentPos": {"type": "number"},
                        "sentNeg": {"type": "number"},
                        "sentNeu": {"type": "number"},
                        "summary": {"type": "string"},
                    },
                    "required": [
                        "id",
                        "title",
                        "years",
                        "score",
                        "scoreClass",
                        "color",
                        "sentPos",
                        "sentNeg",
                        "sentNeu",
                        "summary",
                    ],
                },
            },
            "orgs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "role": {"type": "string"},
                        "dot": {"type": "string"},
                    },
                    "required": ["name", "role", "dot"],
                },
            },
            "coverageVolume": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "count": {"type": "number"},
                        "pct": {"type": "number"},
                        "color": {"type": "string"},
                    },
                    "required": ["label", "count", "pct", "color"],
                },
            },
            "timeline": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "color": {"type": "string"},
                        "text": {"type": "string"},
                        "url": {"type": "string"},
                        "tags": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "label": {"type": "string"},
                                    "cls": {"type": "string"},
                                },
                                "required": ["label", "cls"],
                            },
                        },
                    },
                    "required": ["date", "color", "text", "tags"],
                },
            },
            "outlets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "tone": {"type": "string"},
                        "toneCls": {"type": "string"},
                        "score": {"type": "string"},
                        "scoreColor": {"type": "string"},
                        "url": {"type": "string"},
                    },
                    "required": ["name", "tone", "toneCls", "score", "scoreColor"],
                },
            },
            "inflections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "event": {"type": "string"},
                        "date": {"type": "string"},
                        "shift": {"type": "string"},
                        "shiftColor": {"type": "string"},
                        "driver": {"type": "string"},
                    },
                    "required": ["event", "date", "shift", "shiftColor", "driver"],
                },
            },
            "fundraisingLog": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "year": {"type": "string"},
                        "candidate": {"type": "string"},
                        "amount": {"type": "string"},
                        "amountColor": {"type": "string"},
                        "method": {"type": "string"},
                    },
                    "required": ["year", "candidate", "amount", "amountColor", "method"],
                },
            },
            "fundAssessments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "priority": {"type": "string"},
                        "priCls": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["title", "priority", "priCls", "body"],
                },
            },
            "fundScenarios": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "range": {"type": "string"},
                    },
                    "required": ["title", "body", "range"],
                },
            },
            "campaignPostMortem": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["title", "body"],
                },
            },
            "campaignStrategies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string"},
                        "severityColor": {"type": "string"},
                        "cls": {"type": "string"},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["severity", "severityColor", "cls", "title", "body"],
                },
            },
            "networkTier1": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "rel": {"type": "string"},
                        "strength": {"type": "string"},
                        "strengthColor": {"type": "string"},
                        "dot": {"type": "string"},
                    },
                    "required": ["name", "rel", "strength", "strengthColor", "dot"],
                },
            },
            "mediaNetwork": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "rel": {"type": "string"},
                        "dot": {"type": "string"},
                    },
                    "required": ["name", "rel", "dot"],
                },
            },
            "communityNetwork": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "rel": {"type": "string"},
                        "dot": {"type": "string"},
                    },
                    "required": ["name", "rel", "dot"],
                },
            },
            "riskMetrics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "val": {"type": "string"},
                        "valColor": {"type": "string"},
                        "label": {"type": "string"},
                        "delta": {"type": "string"},
                    },
                    "required": ["val", "valColor", "label", "delta"],
                },
            },
            "risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string"},
                        "severityColor": {"type": "string"},
                        "cls": {"type": "string"},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["severity", "severityColor", "cls", "title", "body"],
                },
            },
            "contributions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "year": {"type": "string"},
                        "recipient": {"type": "string"},
                        "amount": {"type": "string"},
                        "office": {"type": "string"},
                    },
                    "required": ["year", "recipient", "amount", "office"],
                },
            },
            "courtRecords": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "caseNumber": {"type": "string"},
                        "court": {"type": "string"},
                        "title": {"type": "string"},
                        "status": {"type": "string"},
                        "summary": {"type": "string"},
                    },
                    "required": ["date", "caseNumber", "court", "title", "status", "summary"],
                },
            },
            "broadcastAppearances": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "network": {"type": "string"},
                        "program": {"type": "string"},
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "url": {"type": "string"},
                    },
                    "required": ["date", "network", "program", "title", "summary"],
                },
            },
            "summary": {"type": "string"},
            "sentiment": {
                "type": "object",
                "properties": {
                    "positive": {"type": "number"},
                    "negative": {"type": "number"},
                    "neutral": {"type": "number"},
                },
                "required": ["positive", "negative", "neutral"],
            },
            "peakPositive": {
                "type": "object",
                "properties": {
                    "score": {"type": "string"},
                    "date": {"type": "string"},
                    "event": {"type": "string"},
                },
                "required": ["score", "date", "event"],
            },
            "peakNegative": {
                "type": "object",
                "properties": {
                    "score": {"type": "string"},
                    "date": {"type": "string"},
                    "event": {"type": "string"},
                },
                "required": ["score", "date", "event"],
            },
        },
        "required": [
            "subject",
            "eventCount",
            "netSentiment",
            "totalFundraising",
            "electoralResult",
            "phases",
            "orgs",
            "coverageVolume",
            "timeline",
            "outlets",
            "inflections",
            "fundraisingLog",
            "fundAssessments",
            "fundScenarios",
            "campaignPostMortem",
            "campaignStrategies",
            "networkTier1",
            "mediaNetwork",
            "communityNetwork",
            "riskMetrics",
            "risks",
            "contributions",
            "courtRecords",
            "broadcastAppearances",
            "summary",
            "sentiment",
            "peakPositive",
            "peakNegative",
        ],
    }




async def synthesize_intelligence(name: str, raw_data: dict[str, Any]) -> dict[str, Any]:
    client = _get_client()

    prompt = f"""
You are a top-tier political strategist and campaign manager.
I gathered raw data from News, Wikipedia, YouTube, Twitter, Factiva, LexisNexis, campaign finance, and transcript sources about "{name}".

RAW DATA:
{json.dumps(raw_data, indent=2)}

Return only valid JSON for this UI with these exact top-level keys:
subject, eventCount, netSentiment, totalFundraising, electoralResult,
phases, orgs, coverageVolume, timeline, outlets, inflections,
fundraisingLog, fundAssessments, fundScenarios, campaignPostMortem,
campaignStrategies, networkTier1, mediaNetwork, communityNetwork,
riskMetrics, risks, contributions, courtRecords, broadcastAppearances,
summary, sentiment, peakPositive, peakNegative.

Rules:
- Use arrays, never null.
- sentiment must be an object with numeric positive, negative, neutral.
- peakPositive and peakNegative must each have score, date, event.
- phases should have: id, title, years, score, scoreClass, color, sentPos, sentNeg, sentNeu, summary.
- orgs items: name, role, dot.
- coverageVolume items: label, count, pct, color.
- timeline items: date, color, text, url, tags where tags is array of objects with label and cls.
- outlets items: name, tone, toneCls, score, scoreColor, url.
- inflections items: event, date, shift, shiftColor, driver.
- fundraisingLog items: year, candidate, amount, amountColor, method.
- fundAssessments items: title, priority, priCls, body.
- fundScenarios items: title, body, range.
- campaignPostMortem items: title, body.
- campaignStrategies items: severity, severityColor, cls, title, body.
- networkTier1 items: name, rel, strength, strengthColor, dot.
- mediaNetwork/communityNetwork items: name, rel, dot.
- riskMetrics items: val, valColor, label, delta.
- risks items: severity, severityColor, cls, title, body.
- contributions items: year, recipient, amount, office.
- courtRecords items: date, caseNumber, court, title, status, summary.
- broadcastAppearances items: date, network, program, title, summary, url.
- Keep strings concise for UI cards.
""".strip()

    max_retries = 3
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_dashboard_response_schema(),
                ),
            )

            result_text = getattr(response, "text", None)
            if not result_text:
                raise ValueError("Failed to generate intelligence profile")

            data = json.loads(result_text)

            fetched_articles = raw_data.get('articles', []) if isinstance(raw_data, dict) else []
            if "fernando mateo" in name.lower():
                data["fullArchive"] = MATEO_ARCHIVE
                data["eventCount"] = len(MATEO_ARCHIVE)
            elif fetched_articles:
                data["fullArchive"] = fetched_articles
                data["eventCount"] = len(fetched_articles)

            return data

        except Exception as error:
            last_error = error
            error_text = str(error)

            if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
                wait_time = (2 ** attempt) + random.random()
                print(
                    f"Rate limit hit. Retrying in {round(wait_time, 2)}s... "
                    f"(Attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
                continue

            raise

    raise last_error if last_error else RuntimeError("Unknown synthesis error")