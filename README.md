# Instagram AI Control

A secure dashboard starter for an Instagram **Creator** account, built with FastAPI and designed to use Meta's official Instagram Platform APIs.

## Current status

- Responsive Uzbek-language dashboard
- FastAPI health and configuration-status endpoints
- Render deployment blueprint
- No Instagram password collection and no unofficial scraping
- OAuth and account data modules are the next implementation stage

## Run locally

```bash
py -3.11 -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Environment variables

Copy `.env.example` to `.env` when the Meta app is created. Never commit `.env` or access tokens.

- `META_INSTAGRAM_APP_ID`
- `META_INSTAGRAM_APP_SECRET`
- `META_REDIRECT_URI`
- `META_GRAPH_VERSION`
- `SESSION_SECRET`

## Meta integration

The project is intended for Meta's **Instagram API with Instagram Login**. Meta documents support for Instagram professional accounts, including Creator accounts. Exact permissions must be enabled in the Meta app for each feature. Start with profile/media access, then request insights, comments, messaging, and publishing permissions only when those modules are implemented and approved.

Official documentation: https://developers.facebook.com/docs/instagram-platform/

## Deployment

Connect this repository to Render and use the included `render.yaml`. Add the Meta credentials as Render environment variables after creating the Meta app. Do not paste secrets into GitHub, chat, or screenshots.

## Safety and platform limits

Use only official Meta authorization and API endpoints. The app must respect Meta permissions, review requirements, messaging windows, rate limits, and content-publishing rules. It does not access private accounts or bypass Instagram controls.
