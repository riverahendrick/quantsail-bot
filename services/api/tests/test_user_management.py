from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.db.models import User
from app.main import app
from app.public.rate_limit import reset_rate_limiter


@dataclass
class FirebaseUser:
    uid: str
    disabled: bool = False


def _authorized_client(
    engine: sa.Engine, monkeypatch: pytest.MonkeyPatch, role: str = "OWNER"
) -> TestClient:
    """Return a TestClient authorized with the given role."""
    reset_rate_limiter()
    email = f"{role.lower()}@example.com"
    with engine.begin() as conn:
        conn.execute(sa.insert(User).values(id=uuid.uuid4(), email=email, role=role))

    def _verify(_: str) -> dict[str, str]:
        return {"uid": "firebase-uid", "email": email}

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _verify)
    return TestClient(app, headers={"Authorization": "Bearer token"})


def test_create_user_creates_db_and_reset_link(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)

    monkeypatch.setattr("app.api.private.get_firebase_user_by_email", lambda _: None)
    monkeypatch.setattr(
        "app.api.private.create_firebase_user",
        lambda email, password: FirebaseUser(uid="uid-123", disabled=False),
    )
    monkeypatch.setattr("app.api.private.set_firebase_custom_claims", lambda uid, claims: None)
    monkeypatch.setattr(
        "app.api.private.generate_password_reset_link",
        lambda email: "https://reset-link",
    )

    response = client.post(
        "/v1/users",
        json={"email": "new@example.com", "role": "DEVELOPER", "send_reset_link": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "new@example.com"
    assert payload["role"] == "DEVELOPER"
    assert payload["password_reset_link"] == "https://reset-link"

    with migrated_engine.connect() as conn:
        stored = conn.execute(sa.select(User).where(User.email == "new@example.com")).mappings().one()
    assert stored["role"] == "DEVELOPER"


def test_create_user_conflict_when_exists(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)

    with migrated_engine.begin() as conn:
        conn.execute(sa.insert(User).values(id=uuid.uuid4(), email="dup@example.com", role="ADMIN"))

    response = client.post(
        "/v1/users",
        json={"email": "dup@example.com", "role": "ADMIN", "send_reset_link": False},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "USER_EXISTS"


def test_create_user_with_existing_firebase_record(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)

    monkeypatch.setattr(
        "app.api.private.get_firebase_user_by_email",
        lambda _: FirebaseUser(uid="uid-existing", disabled=False),
    )
    monkeypatch.setattr("app.api.private.set_firebase_custom_claims", lambda uid, claims: None)
    monkeypatch.setattr(
        "app.api.private.generate_password_reset_link",
        lambda email: "https://reset-link",
    )

    response = client.post(
        "/v1/users",
        json={"email": "existing@example.com", "role": "ADMIN", "send_reset_link": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "existing@example.com"
    assert payload["role"] == "ADMIN"
    assert payload["password_reset_link"] == "https://reset-link"

def test_list_users_includes_disabled_status(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)

    with migrated_engine.begin() as conn:
        conn.execute(sa.insert(User).values(id=uuid.uuid4(), email="a@example.com", role="OWNER"))
        conn.execute(sa.insert(User).values(id=uuid.uuid4(), email="b@example.com", role="ADMIN"))

    def _get_user(email: str) -> FirebaseUser | None:
        if email == "a@example.com":
            return FirebaseUser(uid="uid-a", disabled=False)
        return None

    monkeypatch.setattr("app.api.private.get_firebase_user_by_email", _get_user)

    response = client.get("/v1/users")

    assert response.status_code == 200
    users = response.json()
    email_to_user = {item["email"]: item for item in users}
    assert email_to_user["a@example.com"]["disabled"] is False
    assert email_to_user["b@example.com"]["disabled"] is None


def test_update_user_role_and_disable(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)

    user_id = uuid.uuid4()
    with migrated_engine.begin() as conn:
        conn.execute(sa.insert(User).values(id=user_id, email="edit@example.com", role="ADMIN"))

    monkeypatch.setattr(
        "app.api.private.get_firebase_user_by_email",
        lambda _: FirebaseUser(uid="uid-edit", disabled=False),
    )
    monkeypatch.setattr("app.api.private.set_firebase_custom_claims", lambda uid, claims: None)
    monkeypatch.setattr(
        "app.api.private.update_firebase_user",
        lambda uid, disabled: FirebaseUser(uid=uid, disabled=disabled),
    )
    monkeypatch.setattr(
        "app.api.private.generate_password_reset_link",
        lambda _: "https://reset-link",
    )

    response = client.patch(
        f"/v1/users/{user_id}",
        json={"role": "DEVELOPER", "disabled": True, "send_reset_link": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "DEVELOPER"
    assert payload["disabled"] is True
    assert payload["password_reset_link"] == "https://reset-link"

    with migrated_engine.connect() as conn:
        updated = conn.execute(sa.select(User).where(User.id == user_id)).mappings().one()
    assert updated["role"] == "DEVELOPER"


def test_update_user_invalid_id(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)

    response = client.patch("/v1/users/not-a-uuid", json={"role": "ADMIN"})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_ID"


def test_update_user_missing_firebase_record(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)

    user_id = uuid.uuid4()
    with migrated_engine.begin() as conn:
        conn.execute(sa.insert(User).values(id=user_id, email="missing@example.com", role="ADMIN"))

    monkeypatch.setattr("app.api.private.get_firebase_user_by_email", lambda _: None)

    response = client.patch(f"/v1/users/{user_id}", json={"role": "ADMIN"})

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "FIREBASE_USER_NOT_FOUND"
