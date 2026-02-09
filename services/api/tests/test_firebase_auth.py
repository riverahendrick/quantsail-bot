from __future__ import annotations

import pytest

from app.auth import firebase as firebase_module


def test_get_firebase_app_reuses_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return the existing Firebase app when available."""
    sentinel_app = object()

    def _get_app() -> object:
        """Return a sentinel app instance."""
        return sentinel_app

    monkeypatch.setattr("app.auth.firebase.firebase_admin.get_app", _get_app)
    monkeypatch.setattr("app.auth.firebase.firebase_admin.initialize_app", pytest.fail)

    assert firebase_module._get_firebase_app() is sentinel_app


def test_get_firebase_app_initializes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Initialize Firebase app when no app exists yet."""
    sentinel_app = object()
    sentinel_cred = object()

    def _get_app() -> object:
        """Raise to simulate missing Firebase app."""
        raise ValueError("no app")

    def _application_default() -> object:
        """Return a placeholder credential object."""
        return sentinel_cred

    def _init_app(cred: object) -> object:
        """Return a sentinel app instance."""
        assert cred is sentinel_cred
        return sentinel_app

    monkeypatch.setattr("app.auth.firebase.firebase_admin.get_app", _get_app)
    monkeypatch.setattr("app.auth.firebase.credentials.ApplicationDefault", _application_default)
    monkeypatch.setattr("app.auth.firebase.firebase_admin.initialize_app", _init_app)

    assert firebase_module._get_firebase_app() is sentinel_app


def test_verify_firebase_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify a Firebase token using the Admin SDK."""
    sentinel_app = object()
    claims: dict[str, object] = {"uid": "firebase-uid"}

    def _get_app() -> object:
        """Return the sentinel Firebase app."""
        return sentinel_app

    def _verify(token: str, app: object, check_revoked: bool) -> dict[str, object]:
        """Return claims for the provided token."""
        assert token == "token"
        assert app is sentinel_app
        assert check_revoked is False
        return claims

    monkeypatch.setattr("app.auth.firebase._get_firebase_app", _get_app)
    monkeypatch.setattr("app.auth.firebase.auth.verify_id_token", _verify)

    assert firebase_module.verify_firebase_token("token") == claims
