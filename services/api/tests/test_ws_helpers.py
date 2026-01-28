from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException, WebSocket

from app.api import ws as ws_module
from app.auth import dependencies as auth_deps
from app.auth.types import AuthUser


def test_parse_cursor_default() -> None:
    """Return zero for missing cursor values."""
    assert ws_module._parse_cursor(None) == 0


def test_parse_cursor_invalid() -> None:
    """Reject invalid cursor values."""
    with pytest.raises(ValueError):
        ws_module._parse_cursor("not-a-number")


def test_build_message_non_dict_payload() -> None:
    """Return empty payload when event payload is not a dict."""
    event = {
        "type": "system.started",
        "payload": ["list"],
        "seq": 1,
    }
    message = ws_module._build_message(event)

    assert message["type"] == "event"
    assert message["payload"] == {}


def test_send_heartbeat() -> None:
    """Emit a heartbeat status payload."""
    messages: list[dict[str, object]] = []

    class DummyWebSocket:
        async def send_json(self, data: dict[str, object]) -> None:
            messages.append(data)

    asyncio.run(ws_module._send_heartbeat(cast(WebSocket, DummyWebSocket())))

    assert messages[0]["type"] == "status"


def test_get_ws_user_maps_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Map HTTP auth errors to WebSocket exceptions."""
    def _fail(_: str) -> AuthUser:
        raise HTTPException(status_code=401, detail={"code": "AUTH_REQUIRED"})

    monkeypatch.setattr(auth_deps, "resolve_user_from_token", _fail)

    stub = SimpleNamespace(headers={}, query_params={"token": "t"})
    ws = cast(WebSocket, stub)

    with pytest.raises(auth_deps.WsAuthError):
        auth_deps.get_ws_user(ws)
