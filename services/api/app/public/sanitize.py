from __future__ import annotations

from typing import Any

FORBIDDEN_KEYS = {
    "exchange_order_id",
    "idempotency_key",
    "ciphertext",
    "nonce",
    "api_key",
    "secret",
    "id",
    "trade_id",
}


def sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove forbidden fields and secrets from an event payload."""
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        key_lower = key.lower()
        if key in FORBIDDEN_KEYS:
            continue
        if "secret" in key_lower or "key" in key_lower:
            continue
        sanitized[key] = value
    return sanitized


def sanitize_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return a sanitized public-safe event response."""
    payload = event.get("payload") or {}
    payload_dict = payload if isinstance(payload, dict) else {}
    return {
        "ts": event.get("ts"),
        "level": event.get("level"),
        "type": event.get("type"),
        "symbol": event.get("symbol"),
        "payload": sanitize_payload(payload_dict),
    }


def sanitize_trade(trade: dict[str, Any]) -> dict[str, Any]:
    """Return a sanitized public-safe trade response."""
    return {
        "symbol": trade.get("symbol"),
        "side": trade.get("side"),
        "status": trade.get("status"),
        "mode": trade.get("mode"),
        "opened_at": trade.get("opened_at"),
        "closed_at": trade.get("closed_at"),
        "entry_price": trade.get("entry_price"),
        "exit_price": trade.get("exit_price"),
        "realized_pnl_usd": trade.get("realized_pnl_usd"),
    }


def sanitize_summary(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    """Return a sanitized summary payload from the latest equity snapshot."""
    if not snapshot:
        return {
            "ts": None,
            "equity_usd": None,
            "cash_usd": None,
            "unrealized_pnl_usd": None,
            "realized_pnl_today_usd": None,
            "open_positions": None,
        }

    return {
        "ts": snapshot.get("ts"),
        "equity_usd": snapshot.get("equity_usd"),
        "cash_usd": snapshot.get("cash_usd"),
        "unrealized_pnl_usd": snapshot.get("unrealized_pnl_usd"),
        "realized_pnl_today_usd": snapshot.get("realized_pnl_today_usd"),
        "open_positions": snapshot.get("open_positions"),
    }
