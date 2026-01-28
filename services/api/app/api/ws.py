from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocketDisconnect

from app.api.redact import redact_payload
from app.auth.dependencies import WsAuthError, get_ws_user
from app.auth.types import Role
from app.db.engine import get_engine
from app.db.events_repo import query_events

router = APIRouter()
ALLOWED_ROLES = {Role.OWNER, Role.CEO, Role.DEVELOPER}


def _poll_interval() -> float:
    """Return the WS poll interval in seconds."""
    return float(os.environ.get("WS_POLL_SECONDS", "1"))


def _heartbeat_interval() -> float:
    """Return the WS heartbeat interval in seconds."""
    return float(os.environ.get("WS_HEARTBEAT_SECONDS", "15"))


def _backlog_limit() -> int:
    """Return the max number of events per WS batch."""
    return int(os.environ.get("WS_BACKLOG_LIMIT", "100"))


def _derive_message_type(event_type: str) -> str:
    """Map event types to WS message categories."""
    if event_type.startswith("trade."):
        return "trade"
    if event_type == "snapshot":
        return "snapshot"
    return "event"


def _parse_cursor(raw: str | None) -> int:
    """Parse the cursor query value into an integer."""
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError("Invalid cursor value.") from exc


def _build_message(event: dict[str, Any]) -> dict[str, Any]:
    """Build a WS envelope from an event row."""
    raw_payload = event.get("payload")
    payload = raw_payload if isinstance(raw_payload, dict) else {}
    return {
        "type": _derive_message_type(str(event.get("type"))),
        "ts": event.get("ts"),
        "cursor": event.get("seq"),
        "event_type": event.get("type"),
        "level": event.get("level"),
        "symbol": event.get("symbol"),
        "trade_id": event.get("trade_id"),
        "public_safe": event.get("public_safe"),
        "payload": redact_payload(payload),
    }


async def _send_heartbeat(websocket: WebSocket) -> None:
    """Send a heartbeat status message."""
    payload = {"ok": True}
    message = {
        "type": "status",
        "ts": datetime.now(timezone.utc),
        "cursor": None,
        "event_type": None,
        "level": "INFO",
        "symbol": None,
        "trade_id": None,
        "public_safe": False,
        "payload": payload,
    }
    await websocket.send_json(jsonable_encoder(message))


async def _stream_events(websocket: WebSocket, cursor: int) -> None:
    """Stream events with backlog + tailing."""
    last_cursor = cursor
    last_sent = time.time()
    poll_interval = _poll_interval()
    heartbeat_interval = _heartbeat_interval()

    events = query_events(
        get_engine(),
        cursor=last_cursor,
        limit=_backlog_limit(),
    )
    for event in events:
        last_cursor = int(event.get("seq", last_cursor))
        await websocket.send_json(jsonable_encoder(_build_message(event)))
        last_sent = time.time()

    while True:
        try:
            await asyncio.wait_for(websocket.receive_text(), timeout=poll_interval)
        except asyncio.TimeoutError:
            pass
        except WebSocketDisconnect:
            break

        events = query_events(
            get_engine(),
            cursor=last_cursor,
            limit=_backlog_limit(),
        )
        for event in events:
            last_cursor = int(event.get("seq", last_cursor))
            await websocket.send_json(jsonable_encoder(_build_message(event)))
            last_sent = time.time()

        if time.time() - last_sent >= heartbeat_interval:
            await _send_heartbeat(websocket)
            last_sent = time.time()


@router.websocket("/ws")
async def websocket_events(websocket: WebSocket) -> None:
    """Stream private events over WebSocket with cursor resume."""
    try:
        user = get_ws_user(websocket)
    except WsAuthError as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return
    except Exception:
        await websocket.close(code=1011, reason="WS_AUTH_ERROR")
        return

    if user.role not in ALLOWED_ROLES:
        await websocket.close(code=1008, reason="RBAC_FORBIDDEN")
        return

    await websocket.accept()

    try:
        cursor = _parse_cursor(websocket.query_params.get("cursor"))
    except ValueError:
        await websocket.close(code=1003, reason="INVALID_CURSOR")
        return

    await _stream_events(websocket, cursor)
