"""Tests for ARM LIVE endpoints."""

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.auth.dependencies import get_current_user
from app.auth.types import AuthUser, Role


@pytest.fixture
def authorized_client() -> TestClient:
    """Return a TestClient with owner auth override."""
    def mock_get_current_user() -> AuthUser:
        return AuthUser(
            email="admin@quantsail.com",
            firebase_uid="test-user",
            role=Role.OWNER,
            user_id="00000000-0000-0000-0000-000000000000",
        )

    app.dependency_overrides[get_current_user] = mock_get_current_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()

def test_arm_flow(authorized_client: TestClient) -> None:
    # 1. Request Token
    # 1. Arm
    response = authorized_client.post("/v1/bot/arm")
    assert response.status_code == 200
    data = response.json()
    assert "arming_token" in data
    token = data["arming_token"]
    
    # 2. Start Live without token (Fail)
    response = authorized_client.post("/v1/bot/start", json={"mode": "live"})
    assert response.status_code == 400
    
    # 3. Start Live with token (Success)
    response = authorized_client.post(
        "/v1/bot/start",
        json={"mode": "live", "arming_token": token}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "started"
    
    # 4. Reuse token (Fail)
    response = authorized_client.post(
        "/v1/bot/start",
        json={"mode": "live", "arming_token": token}
    )
    assert response.status_code == 403
