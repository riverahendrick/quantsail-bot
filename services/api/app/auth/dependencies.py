from __future__ import annotations

from typing import Callable, Mapping

from fastapi import Depends, HTTPException, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.errors import error_detail
from app.auth.firebase import verify_firebase_token
from app.auth.types import AuthUser, Role
from app.db.engine import get_engine
from app.db.queries import get_user_info_by_email

security = HTTPBearer(auto_error=False)


class WsAuthError(Exception):
    """Represents a WebSocket auth failure with a close code."""

    def __init__(self, reason: str, code: int = 1008) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason


def _auth_required() -> HTTPException:
    """Return the standard 401 error for missing/invalid auth."""
    return HTTPException(
        status_code=401,
        detail=error_detail("AUTH_REQUIRED", "Missing or invalid token."),
    )


def _rbac_forbidden() -> HTTPException:
    """Return the standard 403 error for RBAC rejections."""
    return HTTPException(
        status_code=403,
        detail=error_detail("RBAC_FORBIDDEN", "Role not permitted."),
    )


def resolve_user_from_token(token: str) -> AuthUser:
    """Resolve an AuthUser from a Firebase ID token."""
    try:
        decoded = verify_firebase_token(token)
    except Exception as exc:
        raise _auth_required() from exc

    claims: Mapping[str, object] = decoded
    email = claims.get("email")
    firebase_uid = claims.get("uid")
    if not email or not firebase_uid:
        raise _rbac_forbidden()

    user_info = get_user_info_by_email(get_engine(), str(email))
    if not user_info:
        raise _rbac_forbidden()

    user_id_str, role_value = user_info

    try:
        role = Role(role_value)
    except ValueError as exc:
        raise _rbac_forbidden() from exc

    return AuthUser(
        email=str(email),
        firebase_uid=str(firebase_uid),
        role=role,
        user_id=user_id_str,
    )


def _extract_ws_token(websocket: WebSocket) -> str | None:
    """Extract a bearer token from WS headers or query params."""
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", maxsplit=1)[1].strip()
    return websocket.query_params.get("token")


def get_ws_user(websocket: WebSocket) -> AuthUser:
    """Authorize a WebSocket client and return its AuthUser."""
    token = _extract_ws_token(websocket)
    if not token:
        raise WsAuthError("AUTH_REQUIRED")

    try:
        return resolve_user_from_token(token)
    except HTTPException as exc:
        detail = exc.detail
        code = detail.get("code") if isinstance(detail, dict) else "AUTH_REQUIRED"
        raise WsAuthError(str(code)) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser:
    """Verify Firebase JWT and map to a local user role."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise _auth_required()

    return resolve_user_from_token(credentials.credentials)


def require_roles(*allowed: Role) -> Callable[[AuthUser], AuthUser]:
    """Require the current user to be in the allowed role set."""
    allowed_set = set(allowed)

    def _require(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in allowed_set:
            raise _rbac_forbidden()
        return user

    return _require
