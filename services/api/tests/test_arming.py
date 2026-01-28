"""Tests for ARM LIVE endpoints."""

from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.auth.dependencies import get_current_user
from app.auth.types import AuthUser, Role

client = TestClient(app)

# Mock Auth
def mock_get_current_user():
    return AuthUser(email="admin@quantsail.com", firebase_uid="test-user", role=Role.OWNER)

app.dependency_overrides[get_current_user] = mock_get_current_user

def test_arm_flow():
    # 1. Request Token
    with patch("app.api.private.require_roles", return_value={"uid": "test-user"}):
        # We need to bypass the role check dependency which is created at runtime
        # Actually easiest is to mock verify_firebase_token/get_decoded_token which we did
        # But we also need to mock the role check function result?
        # The dependency `require_roles` returns a function.
        pass

    # Simplified test since dependency overrides for dynamic dependencies are tricky
    # We will assume Auth works (tested elsewhere) and focus on logic via direct function calls?
    # No, integration test is better.
    
    # 1. Arm
    response = client.post("/v1/bot/arm")
    assert response.status_code == 200
    data = response.json()
    assert "arming_token" in data
    token = data["arming_token"]
    
    # 2. Start Live without token (Fail)
    response = client.post("/v1/bot/start", json={"mode": "live"})
    assert response.status_code == 400
    
    # 3. Start Live with token (Success)
    response = client.post("/v1/bot/start", json={"mode": "live", "arming_token": token})
    assert response.status_code == 200
    assert response.json()["status"] == "started"
    
    # 4. Reuse token (Fail)
    response = client.post("/v1/bot/start", json={"mode": "live", "arming_token": token})
    assert response.status_code == 403
