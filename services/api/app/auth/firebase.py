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
