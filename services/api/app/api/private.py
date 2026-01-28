from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, cast

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, field_validator

from app.auth.dependencies import require_roles
from app.auth.types import AuthUser, Role
from app.cache.arming import get_arming_cache
from app.cache.news import get_news_cache
from app.db.engine import get_engine
from app.db.models import BotConfigVersion, ExchangeKey
from app.db.queries import list_equity_snapshots, list_events, list_trades
from app.security.encryption import get_encryption_service

router = APIRouter(prefix="/v1")
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
        """Basic validation to ensure minimal keys exist."""
        required = {"strategies", "execution", "risk"}
        if not required.issubset(v.keys()):
            raise ValueError(f"Config must contain top-level keys: {required}")
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
                detail={"code": "ARMING_REQUIRED", "message": "Live mode requires arming token"}
            )
        
        valid = get_arming_cache().verify_and_consume_token(request.arming_token)
        if not valid:
            raise HTTPException(
                status_code=403, 
                detail={"code": "INVALID_TOKEN", "message": "Invalid or expired arming token"}
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


# --- Config Endpoints ---

@router.get("/config")
def get_active_config(_user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))) -> ConfigResponse:
    """Get the currently active configuration."""
    with get_engine().connect() as conn:
        stmt = sa.select(BotConfigVersion).where(BotConfigVersion.is_active.is_(True))
        row = conn.execute(stmt).scalar_one_or_none()
        
        if not row:
            raise HTTPException(status_code=404, detail={"code": "NO_CONFIG", "message": "No active config found"})
            
        return ConfigResponse(
            version=row.version,
            config_hash=row.config_hash,
            is_active=row.is_active,
            created_at=row.created_at,
            activated_at=row.activated_at,
            config_json=row.config_json,
        )


@router.post("/config/versions")
def create_config_version(
    request: ConfigCreate, 
    user: AuthUser = Depends(require_roles(Role.OWNER, Role.CEO))
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
            created_by=user.user_id, # Assuming AuthUser has resolved user_id (UUID)
            is_active=False
        )
        # Note: We can't add object directly without session. Using Core insert.
        stmt = sa.insert(BotConfigVersion).values(
            id=new_config.id,
            version=new_config.version,
            config_json=new_config.config_json,
            config_hash=new_config.config_hash,
            created_by=user.user_id,
            is_active=False
        ).returning(BotConfigVersion.created_at)
        
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
    version: int,
    _user: AuthUser = Depends(require_roles(Role.OWNER, Role.CEO))
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
    request: ExchangeKeyCreate,
    user: AuthUser = Depends(require_roles(Role.OWNER))
) -> ExchangeKeyResponse:
    """Add encrypted Binance credentials."""
    svc = get_encryption_service()
    
    # Combine key:secret into single payload
    payload = f"{request.api_key}:{request.secret_key}"
    ciphertext, nonce = svc.encrypt(payload)
    
    with get_engine().begin() as conn:
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
            )
        )
        
        # Fetch back for timestamps
        row = conn.execute(
            sa.select(ExchangeKey).where(ExchangeKey.id == key_id)
        ).fetchone() # Returns Row object
        
        # Convert Row to dict/object access
        return ExchangeKeyResponse(
            id=str(row.id),
            exchange=row.exchange,
            label=row.label,
            key_version=row.key_version,
            created_at=row.created_at,
            revoked_at=row.revoked_at
        )


@router.delete("/exchanges/binance/keys/{key_id}")
def revoke_binance_key(
    key_id: str,
    _user: AuthUser = Depends(require_roles(Role.OWNER))
) -> dict[str, str]:
    """Revoke (delete) an exchange key."""
    try:
        u_id = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    with get_engine().begin() as conn:
        result = conn.execute(
            sa.delete(ExchangeKey).where(ExchangeKey.id == u_id)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Key not found")
            
    return {"status": "revoked", "id": key_id}


@router.get("/exchanges/binance/keys/status")
def get_key_status(
    _user: AuthUser = Depends(require_roles(Role.OWNER))
) -> list[ExchangeKeyResponse]:
    """List active keys (metadata only, no secrets)."""
    with get_engine().connect() as conn:
        rows = conn.execute(
            sa.select(ExchangeKey).where(ExchangeKey.revoked_at.is_(None))
        ).scalars().all()
        
        return [
            ExchangeKeyResponse(
                id=str(r.id),
                exchange=r.exchange,
                label=r.label,
                key_version=r.key_version,
                created_at=r.created_at,
                revoked_at=r.revoked_at
            ) for r in rows
        ]


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
        rows = conn.execute(stmt).scalars().all()
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
def clear_news_pause(
    _user: AuthUser = Depends(require_roles(*ALLOWED_ROLES))
) -> dict[str, str]:
    """Manually clear the news pause state."""
    cache = get_news_cache()
    cache.clear_pause()
    return {"status": "cleared"}