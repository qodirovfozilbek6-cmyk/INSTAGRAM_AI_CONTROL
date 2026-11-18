from __future__ import annotations

import base64
import hashlib
import os
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "instagram.sqlite3"
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v27.0")
GRAPH_BASE = f"https://graph.instagram.com/{GRAPH_VERSION}"
APP_ID = os.getenv("META_INSTAGRAM_APP_ID", "")
APP_SECRET = os.getenv("META_INSTAGRAM_APP_SECRET", "")
REDIRECT_URI = os.getenv("META_REDIRECT_URI", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "")

app = FastAPI(
    title="Instagram AI Control",
    description="Instagram Creator account dashboard using Meta's official Instagram Login API.",
    version="0.2.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def serializer() -> URLSafeTimedSerializer:
    if not SESSION_SECRET:
        raise HTTPException(503, "SESSION_SECRET is not configured.")
    return URLSafeTimedSerializer(SESSION_SECRET, salt="instagram-oauth-state")


def cipher() -> Fernet:
    if not SESSION_SECRET:
        raise HTTPException(503, "SESSION_SECRET is not configured.")
    key = base64.urlsafe_b64encode(hashlib.sha256(SESSION_SECRET.encode()).digest())
    return Fernet(key)


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with closing(db()) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS instagram_account (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                user_id TEXT NOT NULL,
                username TEXT,
                access_token TEXT NOT NULL,
                token_expires_at INTEGER,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        connection.commit()


@app.on_event("startup")
async def startup() -> None:
    init_db()


def save_account(user_id: str, username: str | None, token: str, expires_in: int | None) -> None:
    encrypted = cipher().encrypt(token.encode()).decode()
    with closing(db()) as connection:
        connection.execute(
            """INSERT INTO instagram_account (id, user_id, username, access_token, token_expires_at, updated_at)
               VALUES (1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(id) DO UPDATE SET user_id=excluded.user_id, username=excluded.username,
               access_token=excluded.access_token, token_expires_at=excluded.token_expires_at,
               updated_at=CURRENT_TIMESTAMP""",
            (str(user_id), username, encrypted, expires_in),
        )
        connection.commit()


def account_row() -> sqlite3.Row | None:
    with closing(db()) as connection:
        return connection.execute("SELECT * FROM instagram_account WHERE id=1").fetchone()


def access_token() -> str:
    row = account_row()
    if not row:
        raise HTTPException(401, "Instagram account is not connected.")
    try:
        return cipher().decrypt(row["access_token"].encode()).decode()
    except InvalidToken:
        raise HTTPException(500, "Stored token could not be decrypted. Reconnect Instagram.")


async def graph_get(path: str, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    query = dict(params or {})
    query["access_token"] = token
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{GRAPH_BASE}/{path.lstrip('/')}", params=query)
    try:
        payload = response.json()
    except ValueError:
        payload = {"error": {"message": "Meta returned an unreadable response."}}
    if response.is_error or "error" in payload:
        message = payload.get("error", {}).get("message", "Instagram API request failed.")
        raise HTTPException(response.status_code if response.is_error else 502, message)
    return payload


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "instagram-ai-control"}


@app.get("/api/status")
async def integration_status() -> dict[str, Any]:
    row = account_row()
    configured = all((APP_ID, APP_SECRET, REDIRECT_URI, SESSION_SECRET))
    return {
        "app": "Instagram AI Control",
        "environment": os.getenv("APP_ENV", "development"),
        "meta_credentials_configured": configured,
        "configured_fields": {
            "app_id": bool(APP_ID),
            "app_secret": bool(APP_SECRET),
            "redirect_uri": bool(REDIRECT_URI),
            "session_secret": bool(SESSION_SECRET),
        },
        "api_version": GRAPH_VERSION,
        "connection": "connected" if row else "not_connected",
        "username": row["username"] if row else None,
    }


@app.get("/auth/instagram")
async def instagram_login() -> RedirectResponse:
    if not all((APP_ID, APP_SECRET, REDIRECT_URI, SESSION_SECRET)):
        raise HTTPException(503, "Meta app settings are incomplete. Configure Render environment variables.")
    state = serializer().dumps({"nonce": secrets.token_urlsafe(24)})
    params = {
        "client_id": APP_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "instagram_business_basic",
        "state": state,
        "enable_fb_login": "0",
        "force_authentication": "1",
    }
    from urllib.parse import urlencode
    return RedirectResponse("https://www.instagram.com/oauth/authorize?" + urlencode(params), status_code=302)


@app.get("/auth/callback")
async def instagram_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    if error:
        return RedirectResponse("/?connect_error=" + error, status_code=303)
    if not code or not state:
        raise HTTPException(400, "Instagram did not return the authorization code and state.")
    try:
        serializer().loads(state, max_age=600)
    except (BadSignature, SignatureExpired):
        raise HTTPException(400, "OAuth state is invalid or expired. Start the connection again.")
    async with httpx.AsyncClient(timeout=25) as client:
        short_response = await client.post(
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": APP_ID,
                "client_secret": APP_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
                "code": code,
            },
        )
        short_data = short_response.json()
        if short_response.is_error or "access_token" not in short_data:
            detail = short_data.get("error_message") or short_data.get("error", {}).get("message") or "Instagram token exchange failed."
            raise HTTPException(502, detail)
        short_token = short_data["access_token"]
        user_id = str(short_data.get("user_id", ""))
        long_response = await client.get(
            "https://graph.instagram.com/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": APP_SECRET,
                "access_token": short_token,
            },
        )
        long_data = long_response.json()
        token = long_data.get("access_token", short_token)
        expires_in = long_data.get("expires_in")
        profile_response = await client.get(
            f"{GRAPH_BASE}/me",
            params={"fields": "user_id,username,name,account_type,media_count,profile_picture_url,website", "access_token": token},
        )
        profile = profile_response.json()
        if profile_response.is_error or "error" in profile:
            detail = profile.get("error", {}).get("message", "Could not read the Instagram profile.")
            raise HTTPException(502, detail)
        user_id = str(profile.get("user_id") or profile.get("id") or user_id)
        save_account(user_id, profile.get("username"), token, expires_in)
    return RedirectResponse("/?connected=1", status_code=303)


@app.get("/api/me")
async def instagram_profile() -> dict[str, Any]:
    token = access_token()
    return await graph_get("me", token, {"fields": "user_id,username,name,account_type,media_count,profile_picture_url,website"})


@app.get("/api/media")
async def instagram_media(limit: int = Query(default=12, ge=1, le=30)) -> dict[str, Any]:
    token = access_token()
    return await graph_get("me/media", token, {"fields": "id,caption,media_type,media_url,permalink,timestamp,thumbnail_url", "limit": limit})


@app.get("/api/insights")
async def instagram_insights() -> dict[str, Any]:
    token = access_token()
    row = account_row()
    if not row:
        raise HTTPException(401, "Instagram account is not connected.")
    # The available metrics depend on the account, API permissions and Meta app review.
    return await graph_get(f"{row['user_id']}/insights", token, {"metric": "reach,profile_views,total_interactions", "period": "day"})


@app.post("/api/disconnect")
async def disconnect_instagram() -> dict[str, bool]:
    with closing(db()) as connection:
        connection.execute("DELETE FROM instagram_account WHERE id=1")
        connection.commit()
    return {"success": True}


@app.get("/api/status/ready")
async def ready() -> dict[str, bool]:
    return {"ready": True}
