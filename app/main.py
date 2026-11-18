from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Instagram AI Control",
    description="A secure dashboard for managing an Instagram Creator account through Meta's official APIs.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "instagram-ai-control"}


@app.get("/api/status")
async def integration_status() -> dict[str, object]:
    required = {
        "app_id": "META_INSTAGRAM_APP_ID",
        "app_secret": "META_INSTAGRAM_APP_SECRET",
        "redirect_uri": "META_REDIRECT_URI",
    }
    configured = {label: bool(os.getenv(key)) for label, key in required.items()}
    return {
        "app": "Instagram AI Control",
        "environment": os.getenv("APP_ENV", "development"),
        "meta_credentials_configured": all(configured.values()),
        "configured_fields": configured,
        "api_version": os.getenv("META_GRAPH_VERSION", "v25.0"),
        "account_type_supported": ["Creator", "Business"],
        "connection": "not_connected",
    }
