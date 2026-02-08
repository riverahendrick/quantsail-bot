"""Backtest result persistence.

Saves GridMetrics and trade data to JSON files for dashboard display
and historical analysis.
"""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quantsail_engine.backtest.grid_backtest import GridMetrics, GridTrade


RESULTS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "data" / "backtest_results"
)


def _serialize(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


def save_grid_result(
    metrics: GridMetrics,
    trades: list[GridTrade],
    output_dir: Path | None = None,
) -> Path:
    """Save a grid backtest result to JSON.

    Args:
        metrics: Grid backtest metrics.
        trades: List of completed trades.
        output_dir: Directory to save results (default: data/backtest_results/).

    Returns:
        Path to the saved JSON file.
    """
    out = output_dir or RESULTS_DIR
    out.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"grid_{metrics.symbol}_{metrics.regime}_{ts}"

    result: dict[str, Any] = {
        "run_id": run_id,
        "strategy": "grid",
        "symbol": metrics.symbol,
        "regime": metrics.regime,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": asdict(metrics),
        "trades": [asdict(t) for t in trades],
    }

    filepath = out / f"{run_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=_serialize)

    return filepath


def save_stress_test_report(
    all_results: list[dict[str, Any]],
    pass_criteria: dict[str, bool],
    output_dir: Path | None = None,
) -> Path:
    """Save a comprehensive stress test report.

    Args:
        all_results: List of per-regime result summaries.
        pass_criteria: Dict of criterion_name -> passed boolean.
        output_dir: Directory to save report.

    Returns:
        Path to the saved JSON report.
    """
    out = output_dir or RESULTS_DIR
    out.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    report: dict[str, Any] = {
        "report_id": f"stress_test_{ts}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pass_criteria": pass_criteria,
        "overall_pass": all(pass_criteria.values()),
        "regime_results": all_results,
    }

    filepath = out / f"stress_test_{ts}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=_serialize)

    return filepath


def load_latest_stress_report(
    results_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Load the most recent stress test report.

    Returns:
        Parsed JSON report or None if no reports exist.
    """
    d = results_dir or RESULTS_DIR
    if not d.exists():
        return None

    reports = sorted(d.glob("stress_test_*.json"), reverse=True)
    if not reports:
        return None

    with open(reports[0], "r", encoding="utf-8") as f:
        result: dict[str, Any] = json.load(f)
        return result
