from pydantic import BaseModel, Field

from app.core.config import SUPPORTED_LANGUAGES


class TokenRequest(BaseModel):
    secret: str = Field(min_length=1, max_length=512)


class TokenResponse(BaseModel):
    token: str
    expiresInSeconds: int


class SessionCreateRequest(BaseModel):
    language: str = Field(default="en")
    userId: str = Field(default="anonymous", max_length=128)


class SessionResponse(BaseModel):
    sessionId: str
    language: str
    userId: str
    createdAt: float
    lastActive: float
    expiresAt: float
    contextLength: int


class SessionCreatedResponse(BaseModel):
    sessionId: str
    expiresAt: float


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    sessionCount: int
    services: dict[str, str]
    missingConfiguration: list[str]


class LanguageResponse(BaseModel):
    supported: tuple[str, ...] = SUPPORTED_LANGUAGES
    labels: dict[str, str] = {"ur": "Urdu", "en": "English", "hi": "Hindi"}


class ErrorEvent(BaseModel):
    code: str
    message: str
    retryable: bool = False
