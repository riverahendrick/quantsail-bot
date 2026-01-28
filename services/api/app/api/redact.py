from __future__ import annotations

from typing import Any

SECRET_KEYS = {
    "exchange_order_id",
    "idempotency_key",
    "ciphertext",
    "nonce",
    "api_key",
    "secret",
}


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove secret fields from payloads for WS streaming."""
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        key_lower = key.lower()
        if key in SECRET_KEYS:
            continue
        if "secret" in key_lower or "key" in key_lower:
            continue
        sanitized[key] = value
    return sanitized
