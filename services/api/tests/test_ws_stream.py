from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.db.events_repo import append_event
from app.db.models import User
from app.main import app


def _insert_user(engine: sa.Engine, email: str, role: str) -> None:
    """Insert a user for WS auth tests."""
    with engine.begin() as conn:
        conn.execute(sa.insert(User).values(id=uuid.uuid4(), email=email, role=role))


def _patch_auth(monkeypatch: pytest.MonkeyPatch, email: str) -> None:
    """Patch Firebase verification for WS tests."""

    def _verify(_: str) -> dict[str, str]:
        """Return a decoded token payload."""
        return {"uid": "firebase-uid", "email": email}

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _verify)


def test_ws_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject WS connections without a token."""
    monkeypatch.setenv("WS_POLL_SECONDS", "0.01")
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect):
        client.websocket_connect("/ws").__enter__()


def test_ws_accepts_query_token(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Allow WS auth via query param token."""
    email = "owner@example.com"
    _insert_user(migrated_engine, email, "OWNER")
    _patch_auth(monkeypatch, email)
    monkeypatch.setenv("WS_POLL_SECONDS", "0.01")
    monkeypatch.setenv("WS_HEARTBEAT_SECONDS", "1000")

    event = append_event(
        migrated_engine,
        event_type="system.started",
        payload={"ok": True},
        level="INFO",
        public_safe=False,
    )

    client = TestClient(app)
    with client.websocket_connect("/ws?cursor=0&token=token") as ws:
        message = ws.receive_json()

    assert message["cursor"] == event["seq"]
    assert message["event_type"] == "system.started"


def test_ws_rejects_invalid_cursor(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject invalid cursor values."""
    email = "owner@example.com"
    _insert_user(migrated_engine, email, "OWNER")
    _patch_auth(monkeypatch, email)
    monkeypatch.setenv("WS_POLL_SECONDS", "0.01")

    client = TestClient(app)
    with client.websocket_connect("/ws?cursor=bad&token=token") as ws:
        with pytest.raises(WebSocketDisconnect) as excinfo:
            ws.receive_text()

    assert excinfo.value.code == 1003


def test_ws_rejects_forbidden_role(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject connections for disallowed roles."""
    email = "admin@example.com"
    _insert_user(migrated_engine, email, "ADMIN")
    _patch_auth(monkeypatch, email)
    monkeypatch.setenv("WS_POLL_SECONDS", "0.01")

    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as excinfo:
        client.websocket_connect("/ws?cursor=0", headers={"Authorization": "Bearer t"}).__enter__()

    assert excinfo.value.code == 1008


def test_ws_handles_auth_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return a server error close code for auth failures."""

    def _fail(_: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("app.api.ws.get_ws_user", _fail)
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as excinfo:
        client.websocket_connect("/ws").__enter__()

    assert excinfo.value.code == 1011


def test_ws_streams_and_resumes(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stream backlog then resume after cursor."""
    email = "owner@example.com"
    _insert_user(migrated_engine, email, "OWNER")
    _patch_auth(monkeypatch, email)
    monkeypatch.setenv("WS_POLL_SECONDS", "0.01")
    monkeypatch.setenv("WS_HEARTBEAT_SECONDS", "1000")

    first = append_event(
        migrated_engine,
        event_type="trade.opened",
        payload={
            "idempotency_key": "secret",
            "secret_hint": "secret",
            "note": "opened",
        },
        level="INFO",
        public_safe=False,
        ts=datetime(2026, 1, 27, tzinfo=timezone.utc),
    )
    second = append_event(
        migrated_engine,
        event_type="snapshot",
        payload={
            "equity_usd": 1000,
            "api_key": "secret",
            "access_key": "secret",
        },
        level="INFO",
        public_safe=False,
        ts=datetime(2026, 1, 27, tzinfo=timezone.utc),
    )

    client = TestClient(app)
    with client.websocket_connect("/ws?cursor=0", headers={"Authorization": "Bearer t"}) as ws:
        message_one = ws.receive_json()
        message_two = ws.receive_json()

    assert message_one["cursor"] == first["seq"]
    assert message_one["type"] == "trade"
    assert message_one["payload"].get("note") == "opened"
    assert "idempotency_key" not in message_one["payload"]
    assert "secret_hint" not in message_one["payload"]

    assert message_two["cursor"] == second["seq"]
    assert message_two["type"] == "snapshot"
    assert "api_key" not in message_two["payload"]
    assert "access_key" not in message_two["payload"]

    third = append_event(
        migrated_engine,
        event_type="system.started",
        payload={"ok": True},
        level="INFO",
        public_safe=False,
    )

    with client.websocket_connect(
        f"/ws?cursor={message_two['cursor']}",
        headers={"Authorization": "Bearer t"},
    ) as ws:
        message_three = ws.receive_json()

    assert message_three["cursor"] == third["seq"]
    assert message_three["event_type"] == "system.started"


def test_ws_streams_new_events_after_connect(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stream new events that arrive after connection."""
    email = "owner@example.com"
    _insert_user(migrated_engine, email, "OWNER")
    _patch_auth(monkeypatch, email)
    monkeypatch.setenv("WS_POLL_SECONDS", "0.01")
    monkeypatch.setenv("WS_HEARTBEAT_SECONDS", "1000")

    client = TestClient(app)
    with client.websocket_connect("/ws?cursor=0", headers={"Authorization": "Bearer t"}) as ws:
        new_event = append_event(
            migrated_engine,
            event_type="system.started",
            payload={"ok": True},
            level="INFO",
            public_safe=False,
        )
        message = ws.receive_json()

    assert message["cursor"] == new_event["seq"]


def test_ws_sends_heartbeat_when_idle(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Emit heartbeat messages when no events arrive."""
    email = "owner@example.com"
    _insert_user(migrated_engine, email, "OWNER")
    _patch_auth(monkeypatch, email)
    monkeypatch.setenv("WS_POLL_SECONDS", "0.01")
    monkeypatch.setenv("WS_HEARTBEAT_SECONDS", "0.01")

    client = TestClient(app)
    with client.websocket_connect("/ws?cursor=0", headers={"Authorization": "Bearer t"}) as ws:
        message = ws.receive_json()

    assert message["type"] == "status"
