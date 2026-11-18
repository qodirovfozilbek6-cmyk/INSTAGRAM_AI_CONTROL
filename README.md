# Instagram AI Control

Instagram Creator/Business account dashboard built with FastAPI and Meta's official Instagram Login API.

## Features in this version

- Official Instagram Login OAuth flow (no Instagram password collection).
- Signed OAuth state validation.
- Short-lived token exchange for a long-lived token when Meta permits it.
- Access token encrypted before storage using a key derived from `SESSION_SECRET`.
- Read the connected professional profile and recent media.
- Attempt account insights where the account and granted permissions support them.
- Local caption-draft helper (not an external generative-AI service yet).
- Disconnect action that removes the locally stored token.

## Deploy on Render

1. Import this repository as a **Web Service** or use the included `render.yaml`.
2. After the first deploy, copy the public service URL.
3. In Render → Environment, set:
   - `META_INSTAGRAM_APP_ID`: App ID from Meta for Developers.
   - `META_INSTAGRAM_APP_SECRET`: App Secret from Meta for Developers.
   - `META_REDIRECT_URI`: `https://YOUR-SERVICE.onrender.com/auth/callback` (replace with your real service hostname).
   - `SESSION_SECRET`: a long random secret. If created from Blueprint, Render generates this value.
   - `META_GRAPH_VERSION`: defaults to `v27.0`.
4. In Meta for Developers, configure the Instagram Login product and add the exact same callback URL as a valid OAuth redirect URI.
5. Add the required Instagram tester/account and grant the `instagram_business_basic` permission for development.
6. Redeploy after environment variables are saved, then open the service and click **Instagram’ni ulash**.

The redirect URI must match exactly in Render and Meta, including HTTPS and the path.

## Environment variables

See `.env.example`. Never commit real secrets or paste them into chats.

## Important limitations

- The Instagram account must be a professional Creator or Business account supported by Meta's Instagram Login API.
- App Review / Advanced Access may be required before other people or additional permissions can use protected features.
- Insights, messaging, comments, and publishing each have separate permission and eligibility requirements. This starter does not claim those features are active merely because OAuth works.
- Inbox/webhooks and content publishing are not enabled in this first connected version.
- The current SQLite database is stored on the service filesystem. On a Render free web service, local files can be lost when the service is recreated or redeployed. For durable production use, configure a persistent disk or managed database before relying on saved tokens.
- Tokens are encrypted at rest, but the application still needs a secure production deployment and a persistent secret. Do not share the Render environment values.

## Local development

```bash
py -3.11 -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000.

## Official references

- https://developers.facebook.com/docs/instagram-platform/
- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/
