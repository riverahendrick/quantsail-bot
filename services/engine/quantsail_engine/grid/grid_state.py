"""Grid state persistence for crash recovery.

Saves grid levels, open orders, cash, and positions to JSON so the bot
can resume after a restart without losing track of what it owns.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STATE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "grid_state"


@dataclass
class GridLevelState:
    """State of a single grid level."""

    price: float
    sell_price: float
    holding: float = 0.0  # qty held at this level
    order_id: str | None = None  # exchange order ID if order is live
    side: str = "buy"  # "buy" or "sell" — what order is active


@dataclass
class CoinGridState:
    """Full state for one coin's grid."""

    symbol: str
    pair: str
    cash: float
    allocation_usd: float
    grid_center: float  # price grid was built around
    num_grids: int
    lower_pct: float
    upper_pct: float
    levels: list[GridLevelState] = field(default_factory=list)
    total_buys: int = 0
    total_sells: int = 0
    total_fees: float = 0.0
    total_pnl: float = 0.0
    num_rebalances: int = 0
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON."""
        d = asdict(self)
        d["last_updated"] = datetime.now(timezone.utc).isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CoinGridState:
        """Deserialize from dict."""
        levels_data = data.pop("levels", [])
        levels = [GridLevelState(**lv) for lv in levels_data]
        return cls(**data, levels=levels)


@dataclass
class PortfolioState:
    """Full portfolio state across all coins."""

    started_at: str = ""
    total_capital_usd: float = 5000.0
    coins: dict[str, CoinGridState] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize."""
        return {
            "started_at": self.started_at,
            "total_capital_usd": self.total_capital_usd,
            "coins": {k: v.to_dict() for k, v in self.coins.items()},
        }


def save_portfolio_state(state: PortfolioState) -> Path:
    """Save portfolio state to JSON file.

    Returns:
        Path to saved state file
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = STATE_DIR / "portfolio_state.json"
    data = state.to_dict()

    # Write atomically (write to tmp, then rename)
    tmp_file = state_file.with_suffix(".tmp")
    with open(tmp_file, "w") as f:
        json.dump(data, f, indent=2)
    tmp_file.replace(state_file)

    logger.debug("Saved portfolio state to %s", state_file)
    return state_file


def load_portfolio_state() -> PortfolioState | None:
    """Load portfolio state from JSON file.

    Returns:
        PortfolioState if file exists, None otherwise
    """
    state_file = STATE_DIR / "portfolio_state.json"
    if not state_file.exists():
        return None

    with open(state_file) as f:
        data = json.load(f)

    coins: dict[str, CoinGridState] = {}
    for symbol, coin_data in data.get("coins", {}).items():
        coins[symbol] = CoinGridState.from_dict(coin_data)

    return PortfolioState(
        started_at=data.get("started_at", ""),
        total_capital_usd=data.get("total_capital_usd", 5000.0),
        coins=coins,
    )


def clear_portfolio_state() -> None:
    """Delete saved state (for fresh start)."""
    state_file = STATE_DIR / "portfolio_state.json"
    if state_file.exists():
        state_file.unlink()
        logger.info("Cleared portfolio state")
