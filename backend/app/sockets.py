import logging

import socketio
from fastapi import HTTPException

from app.core.config import SUPPORTED_LANGUAGES, settings
from app.core.security import validate_jwt
from app.schemas import ErrorEvent
from app.services.assistant import ClientInputError, process_query
from app.services.rate_limiter import rate_limiter
from app.services.session_store import session_store


logger = logging.getLogger(__name__)


def create_socket_server() -> socketio.AsyncServer:
    cors_allowed_origins: str | list[str] = "*" if settings.cors_origins == ["*"] else settings.cors_origins
    sio = socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=cors_allowed_origins,
        logger=settings.environment == "development",
        engineio_logger=False,
        max_http_buffer_size=max(settings.max_frame_bytes, settings.max_audio_bytes) * 2 + 1_000_000,
    )
    register_handlers(sio)
    return sio


def register_handlers(sio: socketio.AsyncServer) -> None:
    # sid -> session_id binding so one socket cannot submit against another
    # client's session, plus an in-flight flag to serialise queries per socket.
    connections: dict[str, str] = {}
    in_flight: set[str] = set()

    async def emit_error(sid: str, error: ErrorEvent) -> None:
        await sio.emit("error:occurred", error.model_dump(), to=sid)

    @sio.event
    async def connect(sid: str, environ: dict, auth: dict | None) -> None:
        logger.info("Socket connected sid=%s", sid)

    @sio.event
    async def disconnect(sid: str) -> None:
        connections.pop(sid, None)
        in_flight.discard(sid)
        logger.info("Socket disconnected sid=%s", sid)

    @sio.on("session:init")
    async def session_init(sid: str, data: dict) -> None:
        if not isinstance(data, dict):
            data = {}
        token = data.get("token", "")
        try:
            validate_jwt(token)
        except HTTPException:
            await emit_error(sid, ErrorEvent(code="AUTH_001", message="Session expired. Please sign in again.", retryable=False))
            return

        language = data.get("language", "en")
        if language not in SUPPORTED_LANGUAGES:
            language = "en"

        # Reuse an existing session on reconnect/language change instead of
        # leaking a new one per init. Two cases rebind rather than recreate:
        #   1. Same socket re-inits (language switch) -> connections[sid].
        #   2. Socket reconnected with a new sid but the client re-submits its
        #      prior sessionId -> rehydrate the context window (spec 5.6).
        existing_id = connections.get(sid) or data.get("sessionId")
        existing = session_store.get(existing_id) if existing_id else None
        if existing is not None:
            existing.language = language
            session = existing
            connections[sid] = session.session_id
        else:
            session = session_store.create(language, str(data.get("userId", "anonymous"))[:128])
            connections[sid] = session.session_id

        await sio.emit(
            "session:init",
            {"sessionId": session.session_id, "language": session.language, "expiresAt": session.expires_at},
            to=sid,
        )

    @sio.on("query:submit")
    async def query_submit(sid: str, data: dict) -> None:
        if not isinstance(data, dict):
            data = {}
        session_id = data.get("sessionId")
        if connections.get(sid) != session_id:
            await emit_error(sid, ErrorEvent(code="AUTH_002", message="Session mismatch. Please restart.", retryable=False))
            return

        session = session_store.get(session_id)
        if session is None:
            connections.pop(sid, None)
            await emit_error(sid, ErrorEvent(code="AUTH_001", message="Session expired. Please restart.", retryable=True))
            return

        if sid in in_flight:
            await emit_error(
                sid,
                ErrorEvent(code="BUSY_001", message="Still working on your last question. One moment.", retryable=True),
            )
            return

        if not rate_limiter.check(session.session_id):
            await emit_error(
                sid,
                ErrorEvent(code="RL_001", message="Rate limit exceeded. Try again shortly.", retryable=True),
            )
            return

        async def emit(event: str, payload: dict[str, object]) -> None:
            await sio.emit(event, payload, to=sid)

        in_flight.add(sid)
        try:
            await process_query(
                session=session,
                frame_base64=data.get("frame", ""),
                audio_base64=data.get("audio", ""),
                emit=emit,
            )
        except ClientInputError as exc:
            await emit_error(sid, exc.event)
        except Exception:
            logger.exception("Unhandled query error sid=%s session=%s", sid, session.session_id)
            await emit_error(sid, ErrorEvent(code="PRC_001", message="Processing failed. Please try again.", retryable=True))
        finally:
            in_flight.discard(sid)

    @sio.on("session:end")
    async def session_end(sid: str, data: dict) -> None:
        if not isinstance(data, dict):
            data = {}
        session_id = data.get("sessionId")
        if connections.get(sid) == session_id:
            session_store.delete(session_id)
            connections.pop(sid, None)
        await sio.emit("session:end", {"status": "deleted"}, to=sid)
