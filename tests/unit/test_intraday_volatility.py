"""Tests for the non-trading intraday-volatility research component."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from quantforge.analytics.intraday_volatility import (
    VolatilityObservation,
    VolatilityRegimeSettings,
    build_volatility_observations,
    validate_volatility_regime,
)
from quantforge.backtest.models import MinuteBar


def settings(**changes: object) -> VolatilityRegimeSettings:
    values: dict[str, object] = {
        "timezone": "America/New_York",
        "predictor_start": time(8, 20),
        "predictor_end": time(8, 50),
        "outcome_end": time(13, 30),
        "training_sessions": 9,
        "validation_sessions": 3,
        "validation_step_sessions": 3,
        "minimum_bucket_sessions": 1,
        "minimum_scored_sessions": 3,
        "minimum_improvement": Decimal("0.05"),
        "minimum_positive_windows": 4,
        "holdout_fraction": Decimal("0.20"),
    }
    values.update(changes)
    return VolatilityRegimeSettings(**values)  # type: ignore[arg-type]


def test_observation_uses_only_predeclared_close_to_close_windows() -> None:
    study_settings = settings(predictor_end=time(8, 22), outcome_end=time(8, 25))
    timezone = ZoneInfo("America/New_York")
    start = datetime(2026, 8, 14, 8, 20, tzinfo=timezone)
    closes = (Decimal("10"), Decimal("12"), Decimal("11"), Decimal("14"), Decimal("13"))
    bars = [
        MinuteBar(
            timestamp=start + timedelta(minutes=index),
            open=close,
            high=close,
            low=close,
            close=close,
            tick_volume=1,
            spread_points=1,
        )
        for index, close in enumerate(closes)
    ]

    observations, excluded = build_volatility_observations(
        bars, settings=study_settings, excluded_session_days=frozenset()
    )

    assert excluded == 0
    assert observations == (
        VolatilityObservation(date(2026, 8, 14), Decimal("2"), Decimal("5")),
    )


def test_predictor_terciles_can_beat_baseline_without_trading_authority() -> None:
    observations = tuple(
        VolatilityObservation(
            session_day=date(2026, 1, 1) + timedelta(days=index),
            predictor=Decimal(str((index % 3) + 1)),
            outcome=Decimal(str(((index % 3) + 1) * 10)),
        )
        for index in range(30)
    )

    report = validate_volatility_regime(
        observations, excluded_sessions=0, settings=settings()
    )

    assert report.gate_decision.passed
    assert report.development_metrics.improvement == Decimal("1")
    assert report.holdout_metrics.improvement == Decimal("1")
    assert len(report.walk_forward_metrics) == 5


def test_gate_rejects_a_model_that_does_not_beat_its_baseline() -> None:
    observations = tuple(
        VolatilityObservation(
            session_day=date(2026, 1, 1) + timedelta(days=index),
            predictor=Decimal(str(index % 3)),
            outcome=Decimal("10") if index % 2 else Decimal("20"),
        )
        for index in range(30)
    )

    report = validate_volatility_regime(
        observations, excluded_sessions=0, settings=settings()
    )

    assert not report.gate_decision.passed
    assert report.gate_decision.reasons
