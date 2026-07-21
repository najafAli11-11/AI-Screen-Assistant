import asyncio
import logging
from contextlib import asynccontextmanager, suppress

import socketio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.logging import configure_logging
from app.services.session_store import session_store
from app.sockets import create_socket_server


configure_logging()
logger = logging.getLogger(__name__)


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(settings.session_cleanup_interval_seconds)
        removed = session_store.cleanup_expired()
        if removed:
            logger.info("Removed %s expired sessions", removed)


def _preload_whisper() -> None:
    from pipeline import stt as stt_pipeline

    stt_pipeline.preload()


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("%s starting version=%s env=%s", settings.app_name, settings.app_version, settings.environment)
    if settings.missing_runtime_dependencies:
        logger.warning("Missing configuration: %s", ", ".join(settings.missing_runtime_dependencies))

    cleanup_task = asyncio.create_task(_cleanup_loop())
    if settings.whisper_preload and settings.environment != "test":
        # Load the Whisper model in the background so the first query does not
        # stall for tens of seconds while weights are read from disk.
        asyncio.get_running_loop().run_in_executor(None, _preload_whisper)

    yield

    cleanup_task.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup_task
    removed = session_store.cleanup_expired()
    logger.info("%s shutting down expired_sessions_removed=%s", settings.app_name, removed)


def create_fastapi_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_origins != ["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(router)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled HTTP error path=%s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


fastapi_app = create_fastapi_app()
sio = create_socket_server()
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
