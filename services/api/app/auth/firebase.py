from __future__ import annotations

from typing import cast

import firebase_admin
from firebase_admin import auth, credentials


def _get_firebase_app() -> firebase_admin.App:
    """Create or return the shared Firebase app instance."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    credential = credentials.ApplicationDefault()
    return firebase_admin.initialize_app(credential)


def verify_firebase_token(token: str) -> dict[str, object]:
    """Verify a Firebase ID token and return decoded claims."""
    app = _get_firebase_app()
    decoded = auth.verify_id_token(token, app=app, check_revoked=False)
    return cast(dict[str, object], decoded)


def get_firebase_user_by_email(email: str) -> auth.UserRecord | None:
    """Return a Firebase user by email, or None if not found."""
    _get_firebase_app()
    try:
        return auth.get_user_by_email(email)
    except Exception as exc:
        if exc.__class__.__name__ == "UserNotFoundError":
            return None
        raise


def create_firebase_user(email: str, password: str) -> auth.UserRecord:
    """Create a Firebase user with an email + password."""
    _get_firebase_app()
    return auth.create_user(email=email, password=password)


def set_firebase_custom_claims(uid: str, claims: dict[str, object]) -> None:
    """Set custom claims for a Firebase user."""
    _get_firebase_app()
    auth.set_custom_user_claims(uid, claims)


def update_firebase_user(uid: str, disabled: bool) -> auth.UserRecord:
    """Enable or disable a Firebase user."""
    _get_firebase_app()
    return auth.update_user(uid=uid, disabled=disabled)


def generate_password_reset_link(email: str) -> str:
    """Generate a Firebase password reset link for an email."""
    _get_firebase_app()
    return auth.generate_password_reset_link(email)
