"""Grid data reader for the API layer.

Reads the grid portfolio state file written by the engine's GridState module.
This is a read-only utility — the API never writes to this file.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# State file is at services/data/grid_state/portfolio_state.json
# API is at services/api/ — so we go up 2 levels to reach services/
_SERVICES_DIR = Path(__file__).resolve().parent.parent.parent
GRID_STATE_FILE = _SERVICES_DIR / "data" / "grid_state" / "portfolio_state.json"
KILL_SWITCH_FILE = _SERVICES_DIR / "data" / "kill_switch_state.json"


def read_grid_state() -> dict[str, Any] | None:
    """Read the grid portfolio state file.

    Returns:
        Parsed JSON dict if file exists, None otherwise.
    """
    if not GRID_STATE_FILE.exists():
        return None
    try:
        with open(GRID_STATE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read grid state: %s", exc)
        return None


def get_strategy_performance() -> list[dict[str, Any]]:
    """Derive strategy performance from grid state.

    Returns a list with one entry: the Grid Trading strategy.
    """
    state = read_grid_state()
    if not state:
        return []

    coins = state.get("coins", {})
    total_buys = sum(c.get("total_buys", 0) for c in coins.values())
    total_sells = sum(c.get("total_sells", 0) for c in coins.values())
    total_pnl = sum(c.get("total_pnl", 0.0) for c in coins.values())
    total_fees = sum(c.get("total_fees", 0.0) for c in coins.values())
    total_trades = total_buys + total_sells

    # Win rate: a "win" in grid trading is any sell that net profits
    # Since grid always sells higher than it buys, win_rate ≈ sells/total
    win_rate = (total_sells / total_trades) if total_trades > 0 else 0.0

    # Profit factor: gross profit / gross loss
    gross_profit: float = max(float(total_pnl), 0.0)
    gross_loss: float = float(abs(total_fees)) if total_pnl >= 0 else float(abs(total_pnl)) + float(total_fees)
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

    avg_trade = (total_pnl / total_trades) if total_trades > 0 else 0.0

    # Find latest update across all coins
    last_signal_at = None
    for coin in coins.values():
        lu = coin.get("last_updated")
        if lu:
            if last_signal_at is None or lu > last_signal_at:
                last_signal_at = lu

    return [{
        "name": "Grid Trading",
        "enabled": len(coins) > 0,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "net_pnl_usd": total_pnl - total_fees,
        "avg_trade_usd": avg_trade,
        "last_signal_at": last_signal_at,
    }]


def get_portfolio_risk() -> dict[str, Any]:
    """Derive portfolio risk metrics from grid state."""
    state = read_grid_state()
    if not state:
        return {
            "total_exposure_usd": 0,
            "open_positions": 0,
            "max_drawdown_pct": 0,
            "current_drawdown_pct": 0,
            "daily_pnl_usd": 0,
            "daily_pnl_pct": 0,
            "var_95_usd": 0,
            "risk_level": "LOW",
        }

    coins = state.get("coins", {})
    total_capital = state.get("total_capital_usd", 5000.0)

    total_exposure = sum(c.get("allocation_usd", 0.0) for c in coins.values())
    open_positions = len(coins)
    total_pnl = sum(c.get("total_pnl", 0.0) for c in coins.values())
    total_fees = sum(c.get("total_fees", 0.0) for c in coins.values())
    net_pnl = total_pnl - total_fees

    pnl_pct = (net_pnl / total_capital * 100) if total_capital > 0 else 0
    drawdown_pct: float = abs(float(min(float(pnl_pct), 0.0)))

    # Simple VaR estimate: 2% of total exposure
    var_95 = total_exposure * 0.02

    # Risk level classification
    if drawdown_pct > 15:
        risk_level = "CRITICAL"
    elif drawdown_pct > 8:
        risk_level = "HIGH"
    elif drawdown_pct > 3:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "total_exposure_usd": total_exposure,
        "open_positions": open_positions,
        "max_drawdown_pct": 20.0,  # configured max
        "current_drawdown_pct": drawdown_pct,
        "daily_pnl_usd": net_pnl,
        "daily_pnl_pct": pnl_pct,
        "var_95_usd": var_95,
        "risk_level": risk_level,
    }


def read_kill_switch_state() -> dict[str, Any]:
    """Read kill switch state from JSON file."""
    if not KILL_SWITCH_FILE.exists():
        return {"is_killed": False, "current_event": None, "history": []}
    try:
        with open(KILL_SWITCH_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"is_killed": False, "current_event": None, "history": []}


def write_kill_switch_state(data: dict[str, Any]) -> None:
    """Write kill switch state to JSON file."""
    KILL_SWITCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(KILL_SWITCH_FILE, "w") as f:
        json.dump(data, f, indent=2)


def trigger_kill_switch(reason: str, triggered_by: str = "operator") -> dict[str, Any]:
    """Trigger the kill switch."""
    state = read_kill_switch_state()
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "triggered_by": triggered_by,
        "details": "Manual kill switch from dashboard",
        "auto_resume_at": None,
    }
    state["is_killed"] = True
    state["current_event"] = event
    history = state.get("history", [])
    history.append(event)
    state["history"] = history
    write_kill_switch_state(state)
    return state


def resume_from_kill() -> dict[str, Any]:
    """Resume trading after kill switch."""
    state = read_kill_switch_state()
    state["is_killed"] = False
    state["current_event"] = None
    write_kill_switch_state(state)
    return state


def get_kill_switch_status() -> dict[str, Any]:
    """Get formatted kill switch status for API response."""
    state = read_kill_switch_state()
    risk = get_portfolio_risk()
    return {
        "is_killed": state.get("is_killed", False),
        "current_event": state.get("current_event"),
        "history_count": len(state.get("history", [])),
        "daily_pnl_pct": risk["daily_pnl_pct"],
        "current_drawdown_pct": risk["current_drawdown_pct"],
        "consecutive_losses": 0,  # TODO: derive from trade history
    }


def get_grid_portfolio() -> dict[str, Any]:
    """Get full grid portfolio data for admin dashboard."""
    state = read_grid_state()
    if not state:
        return {
            "active": False,
            "started_at": None,
            "total_capital_usd": 0,
            "coins": [],
            "summary": {
                "total_buys": 0,
                "total_sells": 0,
                "total_pnl": 0,
                "total_fees": 0,
                "net_pnl": 0,
            },
        }

    coins_data = state.get("coins", {})
    coins_list = []
    total_buys = 0
    total_sells = 0
    total_pnl = 0.0
    total_fees = 0.0

    for symbol, coin in coins_data.items():
        buys = coin.get("total_buys", 0)
        sells = coin.get("total_sells", 0)
        pnl = coin.get("total_pnl", 0.0)
        fees = coin.get("total_fees", 0.0)

        total_buys += buys
        total_sells += sells
        total_pnl += pnl
        total_fees += fees

        levels = coin.get("levels", [])
        active_orders = sum(1 for lv in levels if lv.get("order_id"))
        filled_levels = sum(1 for lv in levels if lv.get("holding", 0) > 0)

        coins_list.append({
            "symbol": symbol,
            "pair": coin.get("pair", f"{symbol}/USDT"),
            "allocation_usd": coin.get("allocation_usd", 0),
            "cash": coin.get("cash", 0),
            "grid_center": coin.get("grid_center", 0),
            "num_grids": coin.get("num_grids", 0),
            "lower_pct": coin.get("lower_pct", 0),
            "upper_pct": coin.get("upper_pct", 0),
            "total_buys": buys,
            "total_sells": sells,
            "total_pnl": pnl,
            "total_fees": fees,
            "net_pnl": pnl - fees,
            "active_orders": active_orders,
            "filled_levels": filled_levels,
            "total_levels": len(levels),
            "num_rebalances": coin.get("num_rebalances", 0),
            "last_updated": coin.get("last_updated"),
        })

    return {
        "active": len(coins_list) > 0,
        "started_at": state.get("started_at"),
        "total_capital_usd": state.get("total_capital_usd", 5000.0),
        "coins": coins_list,
        "summary": {
            "total_buys": total_buys,
            "total_sells": total_sells,
            "total_pnl": total_pnl,
            "total_fees": total_fees,
            "net_pnl": total_pnl - total_fees,
        },
    }


def get_grid_coin_detail(symbol: str) -> dict[str, Any] | None:
    """Get detailed grid data for one coin."""
    state = read_grid_state()
    if not state:
        return None
    coins = state.get("coins", {})
    coin = coins.get(symbol)
    if not coin:
        return None

    # Return coin data with full level details
    return {
        "symbol": symbol,
        "pair": coin.get("pair", f"{symbol}/USDT"),
        "allocation_usd": coin.get("allocation_usd", 0),
        "cash": coin.get("cash", 0),
        "grid_center": coin.get("grid_center", 0),
        "num_grids": coin.get("num_grids", 0),
        "lower_pct": coin.get("lower_pct", 0),
        "upper_pct": coin.get("upper_pct", 0),
        "total_buys": coin.get("total_buys", 0),
        "total_sells": coin.get("total_sells", 0),
        "total_pnl": coin.get("total_pnl", 0),
        "total_fees": coin.get("total_fees", 0),
        "net_pnl": coin.get("total_pnl", 0) - coin.get("total_fees", 0),
        "num_rebalances": coin.get("num_rebalances", 0),
        "last_updated": coin.get("last_updated"),
        "levels": coin.get("levels", []),
    }


def get_public_grid_performance() -> dict[str, Any]:
    """Get sanitized grid performance for public dashboard.

    No API keys, no exact positions, no order IDs exposed.
    """
    state = read_grid_state()
    if not state:
        return {
            "active": False,
            "coins_traded": 0,
            "total_fills": 0,
            "daily_return_pct": 0,
            "total_pnl_usd": 0,
            "strategy": "Grid Trading",
            "last_updated": None,
        }

    coins = state.get("coins", {})
    total_capital = state.get("total_capital_usd", 5000.0)
    total_buys = sum(c.get("total_buys", 0) for c in coins.values())
    total_sells = sum(c.get("total_sells", 0) for c in coins.values())
    total_pnl = sum(c.get("total_pnl", 0.0) for c in coins.values())
    total_fees = sum(c.get("total_fees", 0.0) for c in coins.values())
    net_pnl = total_pnl - total_fees

    pnl_pct = (net_pnl / total_capital * 100) if total_capital > 0 else 0

    # Find latest update
    last_updated = None
    for coin in coins.values():
        lu = coin.get("last_updated")
        if lu and (last_updated is None or lu > last_updated):
            last_updated = lu

    _daily_ret: float = float(pnl_pct)
    _total_pnl: float = float(net_pnl)

    return {
        "active": len(coins) > 0,
        "coins_traded": len(coins),
        "total_fills": total_buys + total_sells,
        "daily_return_pct": round(_daily_ret, 2),
        "total_pnl_usd": round(_total_pnl, 2),
        "strategy": "Grid Trading",
        "last_updated": last_updated,
    }
