import uuid

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.db.models import User
from app.main import app
from app.public.rate_limit import reset_rate_limiter
from main import main as run_main


def test_health_ok(migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    """Return health when authorized."""
    reset_rate_limiter()
    email = "owner@example.com"
    with migrated_engine.begin() as conn:
        conn.execute(sa.insert(User).values(id=uuid.uuid4(), email=email, role="OWNER"))

    def _verify(_: str) -> dict[str, str]:
        """Return a fixed Firebase token payload."""
        return {"uid": "firebase-uid", "email": email}

    monkeypatch.setattr(
        "app.auth.dependencies.verify_firebase_token",
        _verify,
    )

    client = TestClient(app)
    response = client.get("/v1/health", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_main_no_server() -> None:
    """Return success when main is called without starting the server."""
    assert run_main(run_server=False) == 0
