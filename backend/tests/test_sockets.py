"""Tests for the Socket.IO session lifecycle, focusing on reconnection.

These exercise the handler logic directly against a fake AsyncServer so we can
assert on the events emitted back to a client without standing up a real
websocket transport.
"""
import pytest

from app.core.security import create_jwt
from app.services.session_store import session_store
from app.sockets import register_handlers


class FakeServer:
    """Minimal stand-in for socketio.AsyncServer capturing handlers/emits."""

    def __init__(self) -> None:
        self._handlers: dict[str, object] = {}
        self.emitted: list[tuple[str, dict, str | None]] = []

    # Decorators used by register_handlers ---------------------------------
    def event(self, func):
        self._handlers[func.__name__] = func
        return func

    def on(self, name):
        def wrapper(func):
            self._handlers[name] = func
            return func

        return wrapper

    async def emit(self, event, data=None, to=None):
        self.emitted.append((event, data, to))

    # Test helpers ----------------------------------------------------------
    async def call(self, name, *args):
        return await self._handlers[name](*args)

    def last(self, event):
        for name, data, _ in reversed(self.emitted):
            if name == event:
                return data
        return None


@pytest.mark.asyncio
async def test_reconnect_rehydrates_existing_session():
    server = FakeServer()
    register_handlers(server)
    token = create_jwt()

    # Initial connection creates a session.
    await server.call("connect", "sid-1", {}, None)
    await server.call("session:init", "sid-1", {"language": "ur", "token": token})
    first = server.last("session:init")
    session_id = first["sessionId"]
    assert session_id

    # Simulate a dropped socket, then a brand new sid reconnecting with the
    # previously issued sessionId. The server must rebind, not orphan it.
    await server.call("disconnect", "sid-1")
    await server.call("connect", "sid-2", {}, None)
    await server.call(
        "session:init",
        "sid-2",
        {"language": "ur", "token": token, "sessionId": session_id},
    )
    second = server.last("session:init")
    assert second["sessionId"] == session_id

    # A query on the new sid against the rehydrated session must be accepted
    # (no AUTH_002 session mismatch error).
    await server.call("query:submit", "sid-2", {"sessionId": session_id})
    assert server.last("error:occurred") is None or server.last("error:occurred")["code"] != "AUTH_002"

    session_store.delete(session_id)


@pytest.mark.asyncio
async def test_query_rejected_when_session_not_bound_to_socket():
    server = FakeServer()
    register_handlers(server)

    await server.call("connect", "sid-x", {}, None)
    await server.call("query:submit", "sid-x", {"sessionId": "someone-elses-session"})
    error = server.last("error:occurred")
    assert error is not None
    assert error["code"] == "AUTH_002"
