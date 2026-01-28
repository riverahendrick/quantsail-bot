from __future__ import annotations

import uuid
from typing import Callable

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.db.models import User
from app.main import app
from app.public.rate_limit import reset_rate_limiter


def _insert_user(engine: sa.Engine, email: str, role: str) -> None:
    """Insert a user row for auth tests."""
    with engine.begin() as conn:
        conn.execute(sa.insert(User).values(id=uuid.uuid4(), email=email, role=role))


def _mock_verify(email: str) -> Callable[[str], dict[str, str]]:
    """Return a verifier that yields the given email claim."""
    def _verify(_: str) -> dict[str, str]:
        """Return a fixed decoded token payload."""
        return {"uid": "firebase-uid", "email": email}

    return _verify


def _configure_rate_limit() -> None:
    """Reset the rate limiter cache for deterministic tests."""
    reset_rate_limiter()


def test_private_requires_auth(migrated_engine: sa.Engine) -> None:
    """Reject private endpoints without a token."""
    _configure_rate_limit()
    client = TestClient(app)

    response = client.get("/v1/health")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_private_forbidden_role(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return 403 when role is not allowed."""
    _configure_rate_limit()
    email = "admin@example.com"
    _insert_user(migrated_engine, email, "ADMIN")

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _mock_verify(email))

    client = TestClient(app)
    response = client.get("/v1/health", headers={"Authorization": "Bearer token"})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "RBAC_FORBIDDEN"


def test_private_allows_owner(migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    """Allow owner role to access private endpoints."""
    _configure_rate_limit()
    email = "owner@example.com"
    _insert_user(migrated_engine, email, "OWNER")

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _mock_verify(email))

    client = TestClient(app)
    response = client.get("/v1/health", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
