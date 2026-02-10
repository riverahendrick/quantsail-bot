import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add engine root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT.parent / "api"

if str(PROJECT_ROOT) not in sys.path:  # pragma: no cover
    sys.path.append(str(PROJECT_ROOT))

# if str(API_ROOT) not in sys.path:
#     sys.path.append(str(API_ROOT))

# Note: API service path NOT added - tests use stub models only
# When API service is fully implemented, engine will import from app.db.models


@pytest.fixture
def in_memory_db() -> Generator[Session, None, None]:
    """Create an in-memory SQLite database for testing."""
    # Use stub models until API service is ready
    from quantsail_engine.persistence.stub_models import Base

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def clean_config_env() -> Generator[None, None, None]:
    """Ensure QUANTSAIL_* env vars do not interfere with tests unless explicitly set."""
    # Store original values
    original_env = {}
    keys_to_clear = [
        "QUANTSAIL_EXECUTION_MODE",
        "QUANTSAIL_EXECUTION_MIN_PROFIT_USD",
        "QUANTSAIL_RISK_STARTING_CASH_USD",
        "QUANTSAIL_RISK_MAX_RISK_PER_TRADE_PCT",
        "QUANTSAIL_SYMBOLS_ENABLED",
        "QUANTSAIL_SYMBOLS_MAX_CONCURRENT_POSITIONS",
        "MAX_TICKS",
        "ENGINE_CONFIG_PATH",
        "MASTER_KEY"
    ]
    
    for key in keys_to_clear:
        if key in os.environ:
            original_env[key] = os.environ[key]
            os.environ.pop(key, None)
            
    yield
    
    # Restore
    for key, value in original_env.items():
        os.environ[key] = value