import threading
import time
import uuid
from dataclasses import dataclass, field

from app.core.config import settings


@dataclass(slots=True)
class Session:
    session_id: str
    language: str
    user_id: str
    context: list[dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    @property
    def expires_at(self) -> float:
        # Sliding expiry: sessions stay alive while they are being used.
        return self.last_active + settings.session_ttl_minutes * 60

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def context_window(self) -> list[dict[str, str]]:
        return self.context[-3:]

    def touch(self) -> None:
        self.last_active = time.time()

    def add_exchange(self, user_query: str, assistant_response: str) -> None:
        self.context.append({"user": user_query, "assistant": assistant_response})
        self.context = self.context[-3:]
        self.touch()

    def to_dict(self) -> dict[str, object]:
        return {
            "sessionId": self.session_id,
            "language": self.language,
            "userId": self.user_id,
            "createdAt": self.created_at,
            "lastActive": self.last_active,
            "expiresAt": self.expires_at,
            "contextLength": len(self.context),
        }


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, language: str, user_id: str) -> Session:
        session = Session(str(uuid.uuid4()), language, user_id)
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str | None) -> Session | None:
        if not session_id:
            return None
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.is_expired:
                self._sessions.pop(session_id, None)
                return None
            session.touch()
            return session

    def delete(self, session_id: str | None) -> None:
        if session_id:
            with self._lock:
                self._sessions.pop(session_id, None)

    def cleanup_expired(self) -> int:
        with self._lock:
            expired = [sid for sid, session in self._sessions.items() if session.is_expired]
            for sid in expired:
                self._sessions.pop(sid, None)
        return len(expired)

    def __len__(self) -> int:
        self.cleanup_expired()
        return len(self._sessions)


session_store = SessionStore()
