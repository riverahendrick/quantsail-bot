from __future__ import annotations

import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, cast

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.api.errors import error_detail
from app.auth.dependencies import require_roles
from app.auth.firebase import (
    create_firebase_user,
    generate_password_reset_link,
    get_firebase_user_by_email,
    set_firebase_custom_claims,
    update_firebase_user,
)
from app.auth.types import AuthUser, Role
from app.cache.arming import get_arming_cache
from app.cache.news import get_news_cache
from app.db.engine import get_engine
from app.db.models import BotConfigVersion, ExchangeKey, User
from app.db.queries import list_equity_snapshots, list_events, list_trades
from app.schemas.config import BotConfig
from app.security.encryption import get_encryption_service
from app.public.rate_limit import enforce_rate_limit

router = APIRouter(
    prefix="/v1",
    dependencies=[Depends(enforce_rate_limit)],
)
ALLOWED_ROLES = (Role.OWNER, Role.CEO, Role.DEVELOPER)


# --- Schemas ---


class ArmResponse(BaseModel):
    """Response containing arming token."""

    arming_token: str = Field(..., description="Short-lived token to authorize start")
    expires_in_seconds: int = Field(..., description="Token validity duration")


class StartRequest(BaseModel):
    """Request to start the bot."""

    mode: str = Field(..., description="Execution mode: dry-run or live")
    arming_token: str | None = Field(None, description="Required for live mode")


class ConfigCreate(BaseModel):
    """Request to create a new config version."""

    config_json: dict[str, Any] = Field(..., description="Full bot configuration object")

    @field_validator("config_json")
    def validate_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate against BotConfig schema."""
        try:
            BotConfig.model_validate(v)
        except ValidationError as e:
            # Re-raise as ValueError for Pydantic to catch
            raise ValueError(f"Invalid config structure: {e}")
        return v


class ConfigResponse(BaseModel):
    """Response for a config version."""

    version: int
    config_hash: str
    is_active: bool
    created_at: datetime
    activated_at: datetime | None
    config_json: dict[str, Any]


class ExchangeKeyCreate(BaseModel):
    """Request to add an exchange key."""

    label: str = Field(..., description="Human-readable label for this key")
    api_key: str = Field(..., description="Public API Key")
    secret_key: str = Field(..., description="Private Secret Key")


class ExchangeKeyResponse(BaseModel):
    """Safe response for exchange key status (no secrets)."""

    id: str
    exchange: str
    label: str | None
    key_version: int
    created_at: datetime
    revoked_at: datetime | None
    is_active: bool


class NewsIngestRequest(BaseModel):
    """Request to ingest negative high-impact news."""

    title: str = Field(..., description="News headline")
    sentiment: str = Field(..., description="Sentiment: positive, negative, neutral")
    impact: str = Field(..., description="Impact level: high, medium, low")
    source: str = Field(..., description="News source provider")
    pause_minutes: int | None = Field(
        None, ge=1, le=1440, description="Override pause duration (1-1440 minutes)"
    )


class NewsIngestResponse(BaseModel):
    """Response from news ingestion."""

    paused: bool = Field(..., description="Whether trading was paused")
    reason: str = Field(..., description="Reason for pause or rejection")
    pause_until: str | None = Field(None, description="ISO timestamp when pause expires")


class UserCreateRequest(BaseModel):
    """Request to create a new user."""

    email: str = Field(..., description="User email")
    role: Role = Field(..., description="Assigned role")
    send_reset_link: bool = Field(default=True, description="Return password reset link")


class UserUpdateRequest(BaseModel):
    """Request to update user role or disable access."""

    role: Role | None = Field(default=None, description="Updated role")
    disabled: bool | None = Field(default=None, description="Disable or enable user")
    send_reset_link: bool = Field(default=False, description="Return password reset link")


class UserResponse(BaseModel):
    """Response for user management."""

    id: str
    email: str
    role: Role
    created_at: datetime
    disabled: bool | None = None
    password_reset_link: str | None = None


# --- Bot Control Endpoints ---


@router.post("/bot/arm")
def arm_bot(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> ArmResponse:
    """Generate a short-lived arming token for live execution."""
    ttl = 30
    token = get_arming_cache().create_token(ttl_seconds=ttl)
    return ArmResponse(arming_token=token, expires_in_seconds=ttl)


@router.post("/bot/start")
def start_bot(
    request: StartRequest, _user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))
) -> dict[str, str]:
    """Start the trading bot."""
    if request.mode == "live":
        if not request.arming_token:
            raise HTTPException(
                status_code=400,
                detail={"code": "ARMING_REQUIRED", "message": "Live mode requires arming token"},
            )

        valid = get_arming_cache().verify_and_consume_token(request.arming_token)
        if not valid:
            raise HTTPException(
                status_code=403,
                detail={"code": "INVALID_TOKEN", "message": "Invalid or expired arming token"},
            )

    return {"status": "started", "mode": request.mode}


@router.post("/bot/stop")
def stop_bot(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> dict[str, str]:
    """Stop the trading bot."""
    # In MVP, this would signal the engine via DB/Redis/Env
    return {"status": "stopped"}


@router.post("/bot/pause_entries")
def pause_entries(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> dict[str, str]:
    """Pause new entries (exits remain active)."""
    return {"status": "entries_paused"}


@router.post("/bot/resume_entries")
def resume_entries(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> dict[str, str]:
    """Resume new entries."""
    return {"status": "entries_resumed"}


# --- User Management (Owner Only) ---

# Simple in-memory user store for development when DB is not available
DEV_USERS: list[dict[str, Any]] = []


def _resolve_firebase_user(email: str) -> tuple[str | None, bool | None]:
    """Return (uid, disabled) for a Firebase user if present."""
    record = get_firebase_user_by_email(email)
    if not record:
        return None, None
    return record.uid, bool(record.disabled)


@router.get("/users")
def list_users(
    _user: AuthUser = Depends(require_roles(Role.OWNER)),
) -> list[UserResponse]:
    """List users with roles (owner-only)."""
    try:
        with get_engine().connect() as conn:
            rows = conn.execute(sa.select(User).order_by(User.created_at.asc())).mappings().all()

        responses: list[UserResponse] = []
        for row in rows:
            uid, disabled = _resolve_firebase_user(row["email"])
            responses.append(
                UserResponse(
                    id=str(row["id"]),
                    email=row["email"],
                    role=Role(row["role"]),
                    created_at=row["created_at"],
                    disabled=disabled,
                )
            )
        return responses
    except Exception as e:
        # Fallback to development mode when database is not available
        if "DATABASE_URL is required" in str(e):
            # Return development users or empty list
            return [
                UserResponse(
                    id="dev-1",
                    email="hendrickriveravillegas@gmail.com",
                    role=Role.OWNER,
                    created_at=datetime.now(timezone.utc),
                    disabled=False,
                )
            ]
        raise


@router.post("/users")
def create_user(
    request: UserCreateRequest,
    _user: AuthUser = Depends(require_roles(Role.OWNER)),
) -> UserResponse:
    """Create a new user with Firebase + DB role."""
    email = request.email.strip().lower()
    try:
        with get_engine().begin() as conn:
            existing = conn.execute(sa.select(User).where(User.email == email)).scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=error_detail("USER_EXISTS", "User already exists."),
                )

            # Create or reuse Firebase user
            record = get_firebase_user_by_email(email)
            if not record:
                temp_password = secrets.token_urlsafe(16)
                record = create_firebase_user(email=email, password=temp_password)

            set_firebase_custom_claims(record.uid, {"role": request.role.value})

            user_id = uuid.uuid4()
            result = conn.execute(
                sa.insert(User)
                .values(id=user_id, email=email, role=request.role.value)
                .returning(User.created_at)
            ).fetchone()
            created_at = result[0] if result else datetime.now(timezone.utc)

        reset_link = None
        if request.send_reset_link:
            reset_link = generate_password_reset_link(email)

        return UserResponse(
            id=str(user_id),
            email=email,
            role=request.role,
            created_at=created_at,
            disabled=bool(record.disabled),
            password_reset_link=reset_link,
        )
    except Exception as e:
        # Fallback to development mode when database is not available
        if "DATABASE_URL is required" in str(e):
            # Create Firebase user only for development
            record = get_firebase_user_by_email(email)
            if not record:
                temp_password = secrets.token_urlsafe(16)
                record = create_firebase_user(email=email, password=temp_password)

            set_firebase_custom_claims(record.uid, {"role": request.role.value})

            reset_link = None
            if request.send_reset_link:
                reset_link = generate_password_reset_link(email)

            return UserResponse(
                id=f"dev-{uuid.uuid4()}",
                email=email,
                role=request.role,
                created_at=datetime.now(timezone.utc),
                disabled=bool(record.disabled),
                password_reset_link=reset_link,
            )
        raise


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    request: UserUpdateRequest,
    _user: AuthUser = Depends(require_roles(Role.OWNER)),
) -> UserResponse:
    """Update a user's role or disable/enable access."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=error_detail("INVALID_ID", "Invalid user id."))

    with get_engine().begin() as conn:
        row = conn.execute(sa.select(User).where(User.id == user_uuid)).mappings().one_or_none()
        if not row:
            raise HTTPException(
                status_code=404, detail=error_detail("NOT_FOUND", "User not found.")
            )

        if request.role is not None:
            conn.execute(
                sa.update(User).where(User.id == user_uuid).values(role=request.role.value)
            )

    uid, disabled = _resolve_firebase_user(row["email"])
    if not uid:
        raise HTTPException(
            status_code=404,
            detail=error_detail("FIREBASE_USER_NOT_FOUND", "Firebase user not found."),
        )

    if request.role is not None:
        set_firebase_custom_claims(uid, {"role": request.role.value})

    if request.disabled is not None:
        updated = update_firebase_user(uid, disabled=request.disabled)
        disabled = bool(updated.disabled)

    reset_link = None
    if request.send_reset_link:
        reset_link = generate_password_reset_link(row["email"])

    role_value = request.role if request.role is not None else Role(row["role"])
    return UserResponse(
        id=str(row["id"]),
        email=row["email"],
        role=role_value,
        created_at=row["created_at"],
        disabled=disabled,
        password_reset_link=reset_link,
    )


# --- Config Endpoints ---


@router.get("/config")
def get_active_config(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> ConfigResponse:
    """Get the currently active configuration."""
    with get_engine().connect() as conn:
        stmt = sa.select(BotConfigVersion).where(BotConfigVersion.is_active.is_(True))
        row = conn.execute(stmt).mappings().one_or_none()

        if not row:
            raise HTTPException(
                status_code=404, detail={"code": "NO_CONFIG", "message": "No active config found"}
            )

        return ConfigResponse(
            version=row["version"],
            config_hash=row["config_hash"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            activated_at=row["activated_at"],
            config_json=row["config_json"],
        )


@router.post("/config/versions")
def create_config_version(
    request: ConfigCreate, user: AuthUser = Depends(require_roles(Role.OWNER, Role.CEO))
) -> ConfigResponse:
    """Create a new immutable config version."""
    # Canonical hash
    canonical_json = json.dumps(request.config_json, sort_keys=True)
    config_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    with get_engine().begin() as conn:
        # Get next version number
        last_ver = conn.execute(sa.select(sa.func.max(BotConfigVersion.version))).scalar() or 0
        new_ver = last_ver + 1

        # Create
        new_config = BotConfigVersion(
            id=uuid.uuid4(),
            version=new_ver,
            config_json=request.config_json,
            config_hash=config_hash,
            created_by=user.user_id,  # Assuming AuthUser has resolved user_id (UUID)
            is_active=False,
        )
        # Note: We can't add object directly without session. Using Core insert.
        stmt = (
            sa.insert(BotConfigVersion)
            .values(
                id=new_config.id,
                version=new_config.version,
                config_json=new_config.config_json,
                config_hash=new_config.config_hash,
                created_by=user.user_id,
                is_active=False,
            )
            .returning(BotConfigVersion.created_at)
        )

        result = conn.execute(stmt).fetchone()
        created_at = result[0] if result else datetime.now(timezone.utc)

        return ConfigResponse(
            version=new_ver,
            config_hash=config_hash,
            is_active=False,
            created_at=created_at,
            activated_at=None,
            config_json=request.config_json,
        )


@router.post("/config/activate/{version}")
def activate_config(
    version: int, _user: AuthUser = Depends(require_roles(Role.OWNER, Role.CEO))
) -> dict[str, Any]:
    """Activate a specific config version."""
    with get_engine().begin() as conn:
        # Verify exists
        exists = conn.execute(
            sa.select(BotConfigVersion.id).where(BotConfigVersion.version == version)
        ).scalar_one_or_none()

        if not exists:
            raise HTTPException(status_code=404, detail="Config version not found")

        # Deactivate all
        conn.execute(sa.update(BotConfigVersion).values(is_active=False))

        # Activate target
        conn.execute(
            sa.update(BotConfigVersion)
            .where(BotConfigVersion.version == version)
            .values(is_active=True, activated_at=sa.func.now())
        )

        return {"status": "activated", "version": version}


# --- Exchange Key Endpoints ---


@router.post("/exchanges/binance/keys")
def add_binance_key(
    request: ExchangeKeyCreate, user: AuthUser = Depends(require_roles(Role.OWNER))
) -> ExchangeKeyResponse:
    """Add encrypted Binance credentials."""
    svc = get_encryption_service()

    # Combine key:secret into single payload
    payload = f"{request.api_key}:{request.secret_key}"
    ciphertext, nonce = svc.encrypt(payload)

    with get_engine().begin() as conn:
        # Deactivate existing active keys for this exchange
        conn.execute(
            sa.update(ExchangeKey)
            .where(
                ExchangeKey.exchange == "binance",
                ExchangeKey.revoked_at.is_(None),
            )
            .values(is_active=False)
        )

        key_id = uuid.uuid4()
        conn.execute(
            sa.insert(ExchangeKey).values(
                id=key_id,
                exchange="binance",
                label=request.label,
                ciphertext=ciphertext,
                nonce=nonce,
                key_version=1,
                created_by=user.user_id,
                is_active=True,
            )
        )

        # Fetch back for timestamps
        row = conn.execute(
            sa.select(ExchangeKey).where(ExchangeKey.id == key_id)
        ).fetchone()  # Returns Row object

        # Convert Row to dict/object access
        return ExchangeKeyResponse(
            id=str(row.id),
            exchange=row.exchange,
            label=row.label,
            key_version=row.key_version,
            created_at=row.created_at,
            revoked_at=row.revoked_at,
            is_active=row.is_active,
        )


@router.delete("/exchanges/binance/keys/{key_id}")
def revoke_binance_key(
    key_id: str, _user: AuthUser = Depends(require_roles(Role.OWNER))
) -> dict[str, str]:
    """Revoke an exchange key (soft delete)."""
    try:
        u_id = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=error_detail("INVALID_ID", "Invalid key id."))

    with get_engine().begin() as conn:
        result = conn.execute(
            sa.update(ExchangeKey)
            .where(ExchangeKey.id == u_id)
            .values(revoked_at=datetime.now(timezone.utc), is_active=False)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=error_detail("NOT_FOUND", "Key not found."))

    return {"status": "revoked", "id": key_id}


@router.get("/exchanges/binance/keys/status")
def get_key_status(
    _user: AuthUser = Depends(require_roles(Role.OWNER)),
) -> list[ExchangeKeyResponse]:
    """List active keys (metadata only, no secrets)."""
    with get_engine().connect() as conn:
        rows = (
            conn.execute(sa.select(ExchangeKey).where(ExchangeKey.revoked_at.is_(None)))
            .mappings()
            .all()
        )

        return [
            ExchangeKeyResponse(
                id=str(r["id"]),
                exchange=r["exchange"],
                label=r["label"],
                key_version=r["key_version"],
                created_at=r["created_at"],
                revoked_at=r["revoked_at"],
                is_active=r["is_active"],
            )
            for r in rows
        ]


class ExchangeKeyUpdate(BaseModel):
    """Request to update an exchange key (label or rotate secrets)."""

    label: str | None = Field(default=None, description="Updated label")
    api_key: str | None = Field(default=None, description="New API key")
    secret_key: str | None = Field(default=None, description="New secret key")

    @field_validator("secret_key")
    def _validate_rotation(cls, secret_key: str | None, info: Any) -> str | None:
        api_key = info.data.get("api_key") if hasattr(info, "data") else None
        if (api_key and not secret_key) or (secret_key and not api_key):
            raise ValueError("api_key and secret_key must be provided together.")
        return secret_key


@router.patch("/exchanges/binance/keys/{key_id}")
def update_binance_key(
    key_id: str,
    request: ExchangeKeyUpdate,
    _user: AuthUser = Depends(require_roles(Role.OWNER)),
) -> ExchangeKeyResponse:
    """Update label or rotate Binance credentials."""
    try:
        u_id = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=error_detail("INVALID_ID", "Invalid key id."))

    update_values: dict[str, Any] = {}
    if request.label is not None:
        update_values["label"] = request.label

    if request.api_key and request.secret_key:
        svc = get_encryption_service()
        payload = f"{request.api_key}:{request.secret_key}"
        ciphertext, nonce = svc.encrypt(payload)
        update_values["ciphertext"] = ciphertext
        update_values["nonce"] = nonce
        update_values["key_version"] = ExchangeKey.key_version + 1

    if not update_values:
        raise HTTPException(
            status_code=400, detail=error_detail("INVALID_UPDATE", "No fields to update.")
        )

    with get_engine().begin() as conn:
        result = conn.execute(
            sa.update(ExchangeKey)
            .where(ExchangeKey.id == u_id)
            .values(**update_values)
            .returning(
                ExchangeKey.id,
                ExchangeKey.exchange,
                ExchangeKey.label,
                ExchangeKey.key_version,
                ExchangeKey.created_at,
                ExchangeKey.revoked_at,
                ExchangeKey.is_active,
            )
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail=error_detail("NOT_FOUND", "Key not found."))

        return ExchangeKeyResponse(
            id=str(result.id),
            exchange=result.exchange,
            label=result.label,
            key_version=result.key_version,
            created_at=result.created_at,
            revoked_at=result.revoked_at,
            is_active=result.is_active,
        )


@router.post("/exchanges/binance/keys/{key_id}/activate")
def activate_binance_key(
    key_id: str,
    _user: AuthUser = Depends(require_roles(Role.OWNER)),
) -> dict[str, str]:
    """Activate a specific Binance key (deactivate others)."""
    try:
        u_id = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=error_detail("INVALID_ID", "Invalid key id."))

    with get_engine().begin() as conn:
        row = (
            conn.execute(sa.select(ExchangeKey).where(ExchangeKey.id == u_id))
            .mappings()
            .one_or_none()
        )
        if not row:
            raise HTTPException(status_code=404, detail=error_detail("NOT_FOUND", "Key not found."))
        if row["revoked_at"] is not None:
            raise HTTPException(
                status_code=400, detail=error_detail("KEY_REVOKED", "Key is revoked.")
            )

        conn.execute(
            sa.update(ExchangeKey)
            .where(
                ExchangeKey.exchange == row["exchange"],
                ExchangeKey.revoked_at.is_(None),
            )
            .values(is_active=False)
        )
        conn.execute(sa.update(ExchangeKey).where(ExchangeKey.id == u_id).values(is_active=True))

    return {"status": "activated", "id": key_id}


# --- Read-Only Data Endpoints ---


@router.get("/health")
def health(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> dict[str, bool]:
    """Return a basic liveness response for authorized users."""
    return {"ok": True}


@router.get("/health/db")
def health_db(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> dict[str, bool]:
    """Verify the API can connect to Postgres."""
    with get_engine().connect() as connection:
        connection.execute(sa.text("SELECT 1"))
    return {"ok": True}


@router.get("/status")
def status(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> dict[str, str]:
    """Return a minimal bot status payload."""
    value = os.environ.get("BOT_STATUS", "unknown")
    return {"status": value, "ts": datetime.now(timezone.utc).isoformat()}


@router.get("/trades")
def trades(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> list[dict[str, object]]:
    """Return private trades with full fields."""
    data = list_trades(get_engine())
    return cast(list[dict[str, object]], jsonable_encoder(data))


@router.get("/orders")
def orders(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> list[dict[str, object]]:
    """Return private orders (missing in previous audit)."""
    # Simple query implementation
    with get_engine().connect() as conn:
        from app.db.models import Order

        stmt = sa.select(Order).order_by(Order.created_at.desc()).limit(100)
        rows = conn.execute(stmt).mappings().all()
        return cast(list[dict[str, object]], jsonable_encoder(rows))


@router.get("/events")
def events(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> list[dict[str, object]]:
    """Return private events with full fields."""
    data = list_events(get_engine(), public_only=False)
    return cast(list[dict[str, object]], jsonable_encoder(data))


@router.get("/equity")
def equity(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> list[dict[str, object]]:
    """Return private equity snapshots with full fields."""
    data = list_equity_snapshots(get_engine())
    return cast(list[dict[str, object]], jsonable_encoder(data))


# --- News Endpoints ---


@router.post("/news/ingest")
def ingest_news(
    request: NewsIngestRequest, _user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))
) -> NewsIngestResponse:
    """Ingest news and pause entries if negative high-impact."""
    should_pause = request.sentiment == "negative" and request.impact == "high"

    if not should_pause:
        return NewsIngestResponse(
            paused=False,
            reason=f"News filtered: sentiment={request.sentiment}, impact={request.impact}",
            pause_until=None,
        )

    pause_minutes = request.pause_minutes or 60
    cache = get_news_cache()
    cache.set_negative_news_pause(pause_minutes)

    pause_until = datetime.now(timezone.utc) + timedelta(minutes=pause_minutes)

    return NewsIngestResponse(
        paused=True,
        reason=f"Negative high-impact news: {request.title}",
        pause_until=pause_until.isoformat(),
    )


@router.get("/news/status")
def news_status(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> dict[str, bool]:
    """Check if negative news pause is currently active."""
    cache = get_news_cache()
    is_active = cache.is_negative_news_active()
    return {"paused": is_active}


@router.delete("/news/pause")
def clear_news_pause(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> dict[str, str]:
    """Manually clear the news pause state."""
    cache = get_news_cache()
    cache.clear_pause()
    return {"status": "cleared"}


# --- Strategy Performance Endpoints ---


@router.get("/strategies/performance")
def strategies_performance(
    _user: AuthUser = Depends(require_roles(*ALLOWED_ROLES)),
) -> list[dict[str, object]]:
    """Return performance metrics for each strategy (currently Grid Trading)."""
    from app.api.grid_data import get_strategy_performance

    data = get_strategy_performance()
    return cast(list[dict[str, object]], jsonable_encoder(data))


# --- Portfolio Risk Endpoints ---


@router.get("/risk/portfolio")
def risk_portfolio(
    _user: AuthUser = Depends(require_roles(*ALLOWED_ROLES)),
) -> dict[str, object]:
    """Return portfolio risk metrics derived from grid state."""
    from app.api.grid_data import get_portfolio_risk as _get_risk

    return cast(dict[str, object], jsonable_encoder(_get_risk()))


# --- Kill Switch Endpoints ---


@router.get("/risk/kill-switch/status")
def kill_switch_status(
    _user: AuthUser = Depends(require_roles(*ALLOWED_ROLES)),
) -> dict[str, object]:
    """Return kill switch state + risk metrics."""
    from app.api.grid_data import get_kill_switch_status as _ks_status

    return cast(dict[str, object], jsonable_encoder(_ks_status()))


class KillSwitchTriggerRequest(BaseModel):
    """Request to trigger kill switch."""

    reason: str = Field(..., description="Reason for triggering kill switch")


@router.post("/risk/kill-switch/trigger")
def kill_switch_trigger(
    request: KillSwitchTriggerRequest,
    user: AuthUser = Depends(require_roles(*ALLOWED_ROLES)),
) -> dict[str, object]:
    """Trigger the kill switch — stop all trading immediately."""
    from app.api.grid_data import trigger_kill_switch as _trigger

    state = _trigger(reason=request.reason, triggered_by=user.uid)
    return cast(dict[str, object], jsonable_encoder(state))


@router.post("/risk/kill-switch/resume")
def kill_switch_resume(
    _user: AuthUser = Depends(require_roles(*ALLOWED_ROLES)),
) -> dict[str, object]:
    """Resume trading after kill switch."""
    from app.api.grid_data import resume_from_kill as _resume

    state = _resume()
    return cast(dict[str, object], jsonable_encoder(state))


# --- Grid Portfolio Endpoints ---


@router.get("/grid/portfolio")
def grid_portfolio(
    _user: AuthUser = Depends(require_roles(*ALLOWED_ROLES)),
) -> dict[str, object]:
    """Return full grid portfolio data with all coins and levels."""
    from app.api.grid_data import get_grid_portfolio as _grid

    return cast(dict[str, object], jsonable_encoder(_grid()))


@router.get("/grid/{symbol}")
def grid_coin_detail(
    symbol: str,
    _user: AuthUser = Depends(require_roles(*ALLOWED_ROLES)),
) -> dict[str, object]:
    """Return detailed grid data for one coin."""
    from app.api.grid_data import get_grid_coin_detail as _detail

    data = _detail(symbol.upper())
    if data is None:
        raise HTTPException(status_code=404, detail=f"No grid data for {symbol}")
    return cast(dict[str, object], jsonable_encoder(data))
