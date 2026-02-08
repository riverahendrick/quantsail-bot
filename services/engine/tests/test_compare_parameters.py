"""Tests for compare_parameters script."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.compare_parameters import (
    _metrics_summary,
    _print_summary_table,
    compare_profiles,
    run_backtest,
)


@dataclass
class FakeMetrics:
    """Fake BacktestMetrics for testing."""

    net_profit_usd: float = 100.0
    total_return_pct: float = 1.0
    sharpe_ratio: float = 1.5
    sortino_ratio: float = 2.0
    max_drawdown_pct: float = 5.0
    max_drawdown_usd: float = 500.0
    profit_factor: float = 1.8
    win_rate_pct: float = 60.0
    total_trades: int = 20
    winning_trades: int = 12
    losing_trades: int = 8
    avg_trade_usd: float = 5.0
    avg_win_usd: float = 15.0
    avg_loss_usd: float = -10.0
    circuit_breaker_triggers: int = 0
    daily_lock_hits: int = 1
    start_equity: float = 10000.0
    end_equity: float = 10100.0
    start_time: datetime | None = None
    end_time: datetime | None = None
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)


class TestMetricsSummary:
    """Tests for _metrics_summary helper."""

    def test_extracts_all_keys(self) -> None:
        metrics = FakeMetrics()
        summary = _metrics_summary(metrics)  # type: ignore[arg-type]

        assert summary["net_profit_usd"] == 100.0
        assert summary["total_return_pct"] == 1.0
        assert summary["sharpe_ratio"] == 1.5
        assert summary["max_drawdown_pct"] == 5.0
        assert summary["win_rate_pct"] == 60.0
        assert summary["total_trades"] == 20
        assert summary["profit_factor"] == 1.8

    def test_rounds_values(self) -> None:
        metrics = FakeMetrics(net_profit_usd=100.1234567)
        summary = _metrics_summary(metrics)  # type: ignore[arg-type]
        assert summary["net_profit_usd"] == 100.12

    def test_includes_equity_fields(self) -> None:
        metrics = FakeMetrics()
        summary = _metrics_summary(metrics)  # type: ignore[arg-type]
        assert summary["start_equity"] == 10000.0
        assert summary["end_equity"] == 10100.0


class TestPrintSummaryTable:
    """Tests for _print_summary_table."""

    def test_prints_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        results = [
            {"label": "default", "net_profit_usd": 50.0, "total_return_pct": 0.5,
             "sharpe_ratio": 1.0, "sortino_ratio": 1.2, "max_drawdown_pct": 3.0,
             "profit_factor": 1.5, "win_rate_pct": 55.0, "total_trades": 10},
            {"label": "aggressive", "net_profit_usd": 200.0, "total_return_pct": 2.0,
             "sharpe_ratio": 0.8, "sortino_ratio": 0.9, "max_drawdown_pct": 8.0,
             "profit_factor": 1.3, "win_rate_pct": 45.0, "total_trades": 30},
        ]
        _print_summary_table(results)
        output = capsys.readouterr().out
        assert "default" in output
        assert "aggressive" in output
        assert "Net P&L" in output


class TestRunBacktest:
    """Tests for run_backtest."""

    @patch("scripts.compare_parameters.BacktestRunner")
    def test_returns_summary_with_label(self, mock_runner_cls: MagicMock) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = FakeMetrics()
        mock_runner_cls.return_value = mock_runner

        from quantsail_engine.config.models import BotConfig

        config = BotConfig()
        result = run_backtest(config, "dummy.csv", "test-label")

        assert result["label"] == "test-label"
        assert result["net_profit_usd"] == 100.0
        mock_runner.close.assert_called_once()

    @patch("scripts.compare_parameters.BacktestRunner")
    def test_closes_runner_on_error(self, mock_runner_cls: MagicMock) -> None:
        mock_runner = MagicMock()
        mock_runner.run.side_effect = RuntimeError("boom")
        mock_runner_cls.return_value = mock_runner

        from quantsail_engine.config.models import BotConfig

        config = BotConfig()
        with pytest.raises(RuntimeError, match="boom"):
            run_backtest(config, "dummy.csv", "fail-label")

        mock_runner.close.assert_called_once()


class TestCompareProfiles:
    """Tests for compare_profiles."""

    def test_file_not_found_error(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            compare_profiles(
                data_file=tmp_path / "nonexistent.csv",
                output_dir=tmp_path / "out",
            )

    @patch("scripts.compare_parameters.BacktestRunner")
    def test_runs_all_profiles_and_saves_json(
        self, mock_runner_cls: MagicMock, tmp_path: Path
    ) -> None:
        # Create a fake data file
        data_file = tmp_path / "test_data.csv"
        data_file.write_text("timestamp,open,high,low,close,volume\n")

        mock_runner = MagicMock()
        mock_runner.run.return_value = FakeMetrics()
        mock_runner_cls.return_value = mock_runner

        output_dir = tmp_path / "results"
        report = compare_profiles(
            data_file=data_file,
            output_dir=output_dir,
        )

        # Should have default + 3 profiles = 4 results
        assert len(report["results"]) == 4
        labels = [r["label"] for r in report["results"]]
        assert "default" in labels
        assert "conservative" in labels
        assert "moderate" in labels
        assert "aggressive" in labels

        # Verify JSON file was written
        report_file = output_dir / "parameter_comparison.json"
        assert report_file.exists()

        saved = json.loads(report_file.read_text())
        assert saved["starting_cash"] == 10000.0
        assert len(saved["results"]) == 4

    @patch("scripts.compare_parameters.BacktestRunner")
    def test_report_contains_metadata(
        self, mock_runner_cls: MagicMock, tmp_path: Path
    ) -> None:
        data_file = tmp_path / "test_data.csv"
        data_file.write_text("timestamp,open,high,low,close,volume\n")

        mock_runner = MagicMock()
        mock_runner.run.return_value = FakeMetrics()
        mock_runner_cls.return_value = mock_runner

        report = compare_profiles(
            data_file=data_file,
            output_dir=tmp_path / "results",
            starting_cash=5000.0,
        )

        assert report["starting_cash"] == 5000.0
        assert "generated_at" in report
        assert "data_file" in report
        assert "profiles_compared" in report


import json
