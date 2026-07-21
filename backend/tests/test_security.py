import pytest
from fastapi import HTTPException

from app.core.security import exchange_secret_for_token, validate_jwt


def test_exchange_secret_returns_valid_jwt():
    token = exchange_secret_for_token("dev-shared-secret-change-in-prod")
    payload = validate_jwt(token)
    assert "sub" in payload


def test_exchange_secret_rejects_invalid_secret():
    with pytest.raises(HTTPException) as exc:
        exchange_secret_for_token("wrong")
    assert exc.value.status_code == 403
