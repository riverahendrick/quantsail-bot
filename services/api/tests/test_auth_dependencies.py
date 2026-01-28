from __future__ import annotations

from typing import cast

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.dependencies import get_current_user
from app.auth.types import Role


def _credentials() -> HTTPAuthorizationCredentials:
    """Return a valid authorization credentials object."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")


def test_get_current_user_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return 401 when Firebase verification fails."""
    def _raise(_: str) -> dict[str, object]:
        """Raise an error to simulate invalid token verification."""
        raise ValueError("bad token")

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _raise)

    with pytest.raises(HTTPException) as exc:
        get_current_user(_credentials())

    assert exc.value.status_code == 401
    detail = cast(dict[str, str], exc.value.detail)
    assert detail["code"] == "AUTH_REQUIRED"


def test_get_current_user_missing_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return 403 when required claims are missing."""
    def _verify(_: str) -> dict[str, object]:
        """Return a decoded payload with missing email."""
        return {"uid": "firebase-uid"}

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _verify)

    with pytest.raises(HTTPException) as exc:
        get_current_user(_credentials())

    assert exc.value.status_code == 403
    detail = cast(dict[str, str], exc.value.detail)
    assert detail["code"] == "RBAC_FORBIDDEN"


def test_get_current_user_unknown_user(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return 403 when user is not found."""
    def _verify(_: str) -> dict[str, object]:
        """Return a valid decoded payload."""
        return {"uid": "firebase-uid", "email": "missing@example.com"}

    def _get_engine() -> object:
        """Return a placeholder engine object."""
        return object()

    def _lookup(_: object, __: str) -> tuple[str, str] | None:
        """Return no role to simulate a missing user."""
        return None

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _verify)
    monkeypatch.setattr("app.auth.dependencies.get_engine", _get_engine)
    monkeypatch.setattr("app.auth.dependencies.get_user_info_by_email", _lookup)

    with pytest.raises(HTTPException) as exc:
        get_current_user(_credentials())

    assert exc.value.status_code == 403
    detail = cast(dict[str, str], exc.value.detail)
    assert detail["code"] == "RBAC_FORBIDDEN"


def test_get_current_user_invalid_role(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return 403 when role is not recognized."""
    def _verify(_: str) -> dict[str, object]:
        """Return a valid decoded payload."""
        return {"uid": "firebase-uid", "email": "user@example.com"}

    def _get_engine() -> object:
        """Return a placeholder engine object."""
        return object()

    def _lookup(_: object, __: str) -> tuple[str, str]:
        """Return a role that is not part of the enum."""
        return ("uid-123", "HACKER")

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _verify)
    monkeypatch.setattr("app.auth.dependencies.get_engine", _get_engine)
    monkeypatch.setattr("app.auth.dependencies.get_user_info_by_email", _lookup)

    with pytest.raises(HTTPException) as exc:
        get_current_user(_credentials())

    assert exc.value.status_code == 403
    detail = cast(dict[str, str], exc.value.detail)
    assert detail["code"] == "RBAC_FORBIDDEN"


def test_get_current_user_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return an AuthUser when token and role are valid."""
    def _verify(_: str) -> dict[str, object]:
        """Return a valid decoded payload."""
        return {"uid": "firebase-uid", "email": "owner@example.com"}

    def _get_engine() -> object:
        """Return a placeholder engine object."""
        return object()

    def _lookup(_: object, __: str) -> tuple[str, str]:
        """Return a valid role string."""
        return ("uid-123", "OWNER")

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _verify)
    monkeypatch.setattr("app.auth.dependencies.get_engine", _get_engine)
    monkeypatch.setattr("app.auth.dependencies.get_user_info_by_email", _lookup)
    
    user = get_current_user(_credentials())

    assert user.email == "owner@example.com"
    assert user.firebase_uid == "firebase-uid"
    assert user.role is Role.OWNER