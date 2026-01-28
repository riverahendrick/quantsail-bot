from __future__ import annotations

import pytest

from app.auth import firebase as firebase_module


class UserNotFoundError(Exception):
    pass


def test_get_firebase_user_by_email_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_: str):
        raise UserNotFoundError("missing")

    monkeypatch.setattr(firebase_module, "_get_firebase_app", lambda: None)
    monkeypatch.setattr(firebase_module.auth, "get_user_by_email", _raise)

    assert firebase_module.get_firebase_user_by_email("missing@example.com") is None


def test_get_firebase_user_by_email_raises_other_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_: str):
        raise ValueError("boom")

    monkeypatch.setattr(firebase_module, "_get_firebase_app", lambda: None)
    monkeypatch.setattr(firebase_module.auth, "get_user_by_email", _raise)

    with pytest.raises(ValueError):
        firebase_module.get_firebase_user_by_email("bad@example.com")


def test_create_firebase_user_calls_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(firebase_module, "_get_firebase_app", lambda: None)
    monkeypatch.setattr(firebase_module.auth, "create_user", lambda **kwargs: kwargs)

    result = firebase_module.create_firebase_user(email="a@example.com", password="pw")

    assert result["email"] == "a@example.com"


def test_set_firebase_custom_claims_calls_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    def _set(uid: str, claims: dict[str, object]) -> None:
        called["uid"] = uid
        called["claims"] = claims

    monkeypatch.setattr(firebase_module, "_get_firebase_app", lambda: None)
    monkeypatch.setattr(firebase_module.auth, "set_custom_user_claims", _set)

    firebase_module.set_firebase_custom_claims("uid-1", {"role": "OWNER"})

    assert called["uid"] == "uid-1"
    assert called["claims"] == {"role": "OWNER"}


def test_update_firebase_user_calls_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(firebase_module, "_get_firebase_app", lambda: None)
    monkeypatch.setattr(firebase_module.auth, "update_user", lambda **kwargs: kwargs)

    result = firebase_module.update_firebase_user("uid-2", disabled=True)

    assert result["uid"] == "uid-2"
    assert result["disabled"] is True


def test_generate_password_reset_link_calls_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(firebase_module, "_get_firebase_app", lambda: None)
    monkeypatch.setattr(firebase_module.auth, "generate_password_reset_link", lambda email: f"link-{email}")

    link = firebase_module.generate_password_reset_link("reset@example.com")

    assert link == "link-reset@example.com"
