from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.security import exchange_secret_for_token, validate_jwt
from app.schemas import (
    HealthResponse,
    LanguageResponse,
    SessionCreatedResponse,
    SessionCreateRequest,
    SessionResponse,
    TokenRequest,
    TokenResponse,
)
from app.services.session_store import session_store


router = APIRouter()


def require_bearer_token(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    return validate_jwt(authorization[7:])


@router.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@router.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    missing = settings.missing_runtime_dependencies
    return HealthResponse(
        status="degraded" if missing else "healthy",
        version=settings.app_version,
        environment=settings.environment,
        sessionCount=len(session_store),
        missingConfiguration=missing,
        services={
            "whisper": "lazy",
            "claude": "configured" if settings.anthropic_api_key else "missing_key",
            "tts": settings.tts_provider,
        },
    )


@router.get("/api/languages", response_model=LanguageResponse)
async def languages() -> LanguageResponse:
    return LanguageResponse()


@router.post("/api/token", response_model=TokenResponse)
async def get_token(payload: TokenRequest) -> TokenResponse:
    token = exchange_secret_for_token(payload.secret)
    return TokenResponse(token=token, expiresInSeconds=settings.jwt_ttl_minutes * 60)


@router.post("/api/sessions", response_model=SessionCreatedResponse)
async def create_session(
    payload: SessionCreateRequest,
    _: dict = Depends(require_bearer_token),
) -> SessionCreatedResponse:
    language = payload.language if payload.language in {"ur", "en", "hi"} else "en"
    session = session_store.create(language, payload.userId)
    return SessionCreatedResponse(sessionId=session.session_id, expiresAt=session.expires_at)


@router.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    _: dict = Depends(require_bearer_token),
) -> dict[str, object]:
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or expired")
    return session.to_dict()


@router.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: str,
    _: dict = Depends(require_bearer_token),
) -> dict[str, str]:
    session_store.delete(session_id)
    return {"status": "deleted"}


@router.get("/download")
async def download_page() -> HTMLResponse:
    apk_url = settings.apk_download_url or "#"
    disabled = " disabled" if not settings.apk_download_url else ""
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Download AI Screen Assistant</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 0; background: #f7f8fb; color: #172033; }}
    main {{ max-width: 880px; margin: 0 auto; padding: 40px 20px; }}
    .hero {{ background: white; border: 1px solid #dde3ee; border-radius: 8px; padding: 28px; }}
    a.button {{ display: inline-block; margin: 18px 0; padding: 14px 20px; background: #0b63ce; color: white; text-decoration: none; border-radius: 8px; font-weight: 700; }}
    a.button[disabled] {{ pointer-events: none; background: #94a3b8; }}
    li {{ margin: 10px 0; }}
    code {{ background: #edf2f7; padding: 2px 6px; border-radius: 4px; }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>AI Screen Assistant</h1>
      <p>Android screen guidance with spoken Urdu, Hindi, and English instructions.</p>
      <a class="button" href="{apk_url}"{disabled}>Download APK</a>
      <p>Version {settings.app_version}. The app needs screen capture, microphone, overlay, and internet permissions so it can see the current screen, hear the question, and speak the answer.</p>
    </section>
    <h2>Install Steps</h2>
    <ol>
      <li>Open this page in Chrome on the Android phone.</li>
      <li>Tap <strong>Download APK</strong>, then open the downloaded file.</li>
      <li>If Android asks, enable <strong>Allow from this source</strong> for Chrome.</li>
      <li>Tap <strong>Install</strong>, then open the app.</li>
      <li>Approve screen capture, microphone, and overlay permissions during onboarding.</li>
    </ol>
    <h2>Device Settings</h2>
    <p>Samsung: Settings &gt; Biometrics and security &gt; Install unknown apps &gt; Chrome &gt; Allow.</p>
    <p>Stock Android: Settings &gt; Apps &gt; Special app access &gt; Install unknown apps &gt; Chrome &gt; Allow.</p>
  </main>
</body>
</html>"""
    return HTMLResponse(content=html)
