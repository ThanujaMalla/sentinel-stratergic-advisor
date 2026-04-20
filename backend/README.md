# Sentinel Backend API

This is the FastAPI backend for the Sentinel Strategic Advisor.

## Features

- **Asynchronous Ingestion**: Concurrently fetches data from 10+ sources.
- **AI Synthesis**: Uses Gemini 3 Flash preview to generate strategic insights.
- **Caching**: MongoDB storage for raw and synthesized data.
- **Structured Logging**: Uses `loguru` for production-grade logging.
- **Pydantic Validation**: Strong typing and validation for all data models.

## Structure

- `app/api/v1/`: Versioned API endpoints.
- `app/services/`: Business logic and external service integrations.
- `app/connectors/`: Low-level API connectors for specific sources.
- `app/db.py`: Asynchronous MongoDB client and repository functions.
- `app/config.py`: Centralized configuration using `pydantic-settings`.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up environment variables in `.env`.
3. Run with Uvicorn:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## API Documentation

Access the following URLs while the server is running:
- **Swagger UI**: `/api/docs`
- **ReDoc**: `/api/redoc`
- **Health Check**: `/api/health`
