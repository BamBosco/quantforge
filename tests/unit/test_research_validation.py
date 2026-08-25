from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from quantforge.backtest.validation import (
    ResearchGate,
    ValidationSession,
    evaluate_cost_stress,
    evaluate_performance,
    run_research_validation,
    split_chronologically,
)
from quantforge.config.research_validation import load_research_validation_settings


def sessions(values: list[str | None]) -> tuple[ValidationSession, ...]:
    start = date(2026, 1, 1)
    return tuple(
        ValidationSession(
            session_day=start + timedelta(days=index),
            r_multiple=Decimal(value) if value is not None else None,
        )
        for index, value in enumerate(values)
    )


def test_performance_reports_r_drawdown_and_profit_factor() -> None:
    metrics = evaluate_performance(sessions(["1", "-2", "3", None]))

    assert metrics.completed_trades == 3
    assert metrics.total_r == Decimal("2")
    assert metrics.mean_r == Decimal(2) / Decimal(3)
    assert metrics.maximum_drawdown_r == Decimal("2")
    assert metrics.profit_factor == Decimal("2")


def test_split_reserves_final_contiguous_holdout_sessions() -> None:
    split = split_chronologically(
        sessions(["1"] * 10), holdout_fraction=Decimal("0.20")
    )

    assert len(split.development) == 8
    assert len(split.holdout) == 2
    assert split.development[-1].session_day < split.holdout[0].session_day


def test_cost_stress_rejects_noncomparable_session_dates() -> None:
    first = sessions(["1", "1"])
    second = (
        ValidationSession(date(2026, 1, 1), Decimal("1")),
        ValidationSession(date(2026, 1, 3), Decimal("1")),
    )

    try:
        evaluate_cost_stress({"first": first, "second": second})
    except ValueError as error:
        assert "identical session dates" in str(error)
    else:
        raise AssertionError("noncomparable cost scenarios must be rejected")


def test_gate_rejects_negative_holdout_even_with_positive_training_windows() -> None:
    protocol = load_research_validation_settings(
        Path("config/research/standard_validation_protocol.toml")
    )
    observations = sessions(["1"] * 596 + ["-1"] * 150)
    report = run_research_validation(
        {"recorded_spread_only": observations},
        holdout_fraction=protocol.holdout_fraction,
        training_sessions=protocol.walk_forward.training_sessions,
        validation_sessions=protocol.walk_forward.validation_sessions,
        step_sessions=protocol.walk_forward.step_sessions,
        gate=ResearchGate(
            minimum_completed_trades=100,
            require_positive_total_r=True,
            require_positive_mean_r=True,
            require_positive_holdout=True,
            minimum_positive_walk_forward_windows=2,
        ),
    )

    assert report.gate_decision.passed is False
    assert any("holdout" in reason for reason in report.gate_decision.reasons)
