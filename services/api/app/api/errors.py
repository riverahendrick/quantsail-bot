from __future__ import annotations

from typing import TypedDict


class ErrorDetail(TypedDict):
    code: str
    message: str


def error_detail(code: str, message: str) -> ErrorDetail:
    """Create a standardized error detail payload."""
    return {"code": code, "message": message}
