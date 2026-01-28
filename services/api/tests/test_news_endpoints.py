"""Tests for news ingestion endpoints."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.cache.news import reset_news_cache
from app.db.models import User
from app.main import app


def _authorized_client(
    engine: sa.Engine, monkeypatch: pytest.MonkeyPatch, role: str = "OWNER"
) -> TestClient:
    """Return a TestClient authorized with the given role."""
    email = f"{role.lower()}@example.com"
    with engine.begin() as conn:
        conn.execute(sa.insert(User).values(id=uuid.uuid4(), email=email, role=role))

    def _verify(_: str) -> dict[str, str]:
        return {"uid": "firebase-uid", "email": email}

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _verify)
    return TestClient(app, headers={"Authorization": "Bearer token"})


def test_ingest_negative_high_impact_news_triggers_pause(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test negative high-impact news triggers pause."""
    reset_news_cache()
    client = _authorized_client(migrated_engine, monkeypatch)

    response = client.post(
        "/v1/news/ingest",
        json={
            "title": "Major exchange hack",
            "sentiment": "negative",
            "impact": "high",
            "source": "cryptopanic",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["paused"] is True
    assert "Major exchange hack" in data["reason"]
    assert data["pause_until"] is not None

    # Verify cache is active
    status_response = client.get("/v1/news/status")
    assert status_response.status_code == 200
    assert status_response.json()["paused"] is True

    reset_news_cache()


def test_ingest_positive_news_does_not_pause(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test positive news does not trigger pause."""
    reset_news_cache()
    client = _authorized_client(migrated_engine, monkeypatch)

    response = client.post(
        "/v1/news/ingest",
        json={
            "title": "Bitcoin reaches new ATH",
            "sentiment": "positive",
            "impact": "high",
            "source": "cryptopanic",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["paused"] is False
    assert "filtered" in data["reason"]

    reset_news_cache()


def test_ingest_negative_low_impact_does_not_pause(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test negative low-impact news does not trigger pause."""
    reset_news_cache()
    client = _authorized_client(migrated_engine, monkeypatch)

    response = client.post(
        "/v1/news/ingest",
        json={
            "title": "Minor price dip",
            "sentiment": "negative",
            "impact": "low",
            "source": "cryptopanic",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["paused"] is False
    assert "filtered" in data["reason"]

    reset_news_cache()


def test_ingest_with_custom_pause_duration(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test custom pause duration override."""
    reset_news_cache()
    client = _authorized_client(migrated_engine, monkeypatch)

    response = client.post(
        "/v1/news/ingest",
        json={
            "title": "Critical security alert",
            "sentiment": "negative",
            "impact": "high",
            "source": "cryptopanic",
            "pause_minutes": 120,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["paused"] is True

    reset_news_cache()


def test_clear_news_pause(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test manually clearing news pause."""
    reset_news_cache()
    client = _authorized_client(migrated_engine, monkeypatch)

    # Set pause
    client.post(
        "/v1/news/ingest",
        json={
            "title": "Test",
            "sentiment": "negative",
            "impact": "high",
            "source": "test",
        },
    )

    # Verify active
    status = client.get("/v1/news/status")
    assert status.json()["paused"] is True

    # Clear
    clear_response = client.delete("/v1/news/pause")
    assert clear_response.status_code == 200

    # Verify cleared
    status = client.get("/v1/news/status")
    assert status.json()["paused"] is False

    reset_news_cache()


def test_news_endpoints_require_auth() -> None:
    """Test news endpoints require authentication."""
    reset_news_cache()
    client = TestClient(app)

    # No auth header
    response = client.post(
        "/v1/news/ingest",
        json={
            "title": "Test",
            "sentiment": "negative",
            "impact": "high",
            "source": "test",
        },
    )
    assert response.status_code == 401

    response = client.get("/v1/news/status")
    assert response.status_code == 401

    response = client.delete("/v1/news/pause")
    assert response.status_code == 401

    reset_news_cache()
