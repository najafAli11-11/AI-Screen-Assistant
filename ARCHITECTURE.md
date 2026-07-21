# AI Screen Assistant Architecture

## Product Purpose

AI Screen Assistant provides real-time guidance for users who are unfamiliar with technology. A client captures the current screen and a spoken question, the backend transcribes the audio, sends the screenshot and transcript to one multimodal model call, and streams simple spoken and captioned instructions back to the user.

## Production Assessment

The original repository was a functional prototype, not production-ready. It had a monolithic backend entrypoint, hard-coded browser secrets, permissive CORS defaults, no typed request models, no tests, no Android Gradle project, incomplete APK download configuration, and no deployable web image. The current implementation keeps the intended stack and hardens the architecture around explicit boundaries.

## Technology Choices

Python + FastAPI remains the backend stack because the app needs local Whisper, async streaming, simple typed APIs, and Docker-friendly ML dependencies.

Socket.IO remains the realtime transport because reconnection, event naming, and browser/Android client support are already central to the product.

React + TypeScript remains the web stack because the desktop client is a capture-heavy operational UI with strong browser API usage and compile-time contracts.

Kotlin remains the Android layer because MediaProjection, foreground services, AudioRecord, and overlays are Android-native capabilities that are not safely handled by a pure web app.

In-memory sessions remain the MVP store. Redis should replace it when the backend is scaled beyond one instance.

## System Architecture

Client input:
- Desktop web uses `getDisplayMedia` for screen frames and Web Audio for WAV microphone capture.
- Android uses MediaProjection, AudioRecord, a foreground service, and overlay UI.

Backend flow:
- REST exchanges a pre-shared access code for a short-lived JWT.
- Socket.IO initializes a session using the JWT.
- `query:submit` validates payload size, decodes frame/audio, transcribes audio with Whisper, streams Claude multimodal guidance, splits complete sentences, generates TTS audio, and emits ordered events.

Client output:
- Text tokens render immediately.
- Complete steps render as captions.
- MP3 chunks play through an ordered queue by sentence index.

## Folder Structure

`backend/app/core` contains configuration, security, and logging.

`backend/app/api` contains typed REST routes.

`backend/app/services` contains session, rate limiting, and assistant orchestration logic.

`backend/pipeline` contains provider integrations for STT, LLM, translation, and TTS.

`web/src/components` contains capture, playback, and caption primitives.

`web/src/hooks` contains realtime state.

`android/app/src/main` contains native Android service, overlay, audio, and socket code.

## API Design

REST:
- `POST /api/token`
- `POST /api/sessions`
- `GET /api/sessions/{id}`
- `DELETE /api/sessions/{id}`
- `GET /api/health`
- `GET /api/languages`
- `GET /download`

Socket.IO:
- Client emits `session:init`, `query:submit`, `session:end`.
- Server emits `transcript:ready`, `response:token`, `response:sentence`, `response:audio`, `response:done`, `error:occurred`.

## Authentication

The web and Android clients exchange `PRE_SHARED_SECRET` for a JWT via `/api/token`. REST session routes and socket session initialization validate the JWT. The browser no longer embeds a default shared secret; the user enters the access code for a demo session.

## Error Handling

Errors are emitted with a stable code, user-safe message, and retry flag. Backend logs keep operational failures visible without logging screen frames or audio payloads.

## Logging

Backend logging is configured centrally in `app/core/logging.py`. Production deployments should ship stdout logs to the host platform log aggregator.

## Configuration

All secrets and runtime values live in environment variables documented in `.env.example`. Pydantic settings parse and validate the backend configuration. Android server URL and access secret are Gradle properties so secrets do not need to be committed.

## Deployment

Backend is packaged as a non-root Python container running Uvicorn. Web is built into static assets and served by Nginx. `docker-compose.yml` runs both locally. Android debug builds are wired into CI; release signing needs a keystore provided outside the repository.

## Testing

Backend tests cover auth, session context, rate limiting, and health endpoint behavior. CI runs Ruff, Pytest, web typecheck/build, Android debug build, and Docker image builds.
