from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import fastapi_app


def test_health_endpoint_reports_configuration_state():
    client = TestClient(fastapi_app)
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == settings.app_version
    assert "services" in body
    assert "claude" in body["services"]
