"""Offline, price-only validation of an intraday XAUUSD volatility forecast."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_CEILING, Decimal
from zoneinfo import ZoneInfo

from quantforge.backtest.models import MinuteBar
from quantforge.backtest.replay import complete_minute_window


@dataclass(frozen=True, slots=True)
class VolatilityRegimeSettings:
    """Frozen calendar and validation settings for the risk-regime study."""

    timezone: str
    predictor_start: time
    predictor_end: time
    outcome_end: time
    training_sessions: int
    validation_sessions: int
    validation_step_sessions: int
    minimum_bucket_sessions: int
    minimum_scored_sessions: int
    minimum_improvement: Decimal
    minimum_positive_windows: int
    holdout_fraction: Decimal

    def __post_init__(self) -> None:
        if not self.predictor_start < self.predictor_end < self.outcome_end:
            raise ValueError("volatility-regime times must be strictly ordered")
        if (
            min(
                self.training_sessions,
                self.validation_sessions,
                self.validation_step_sessions,
                self.minimum_bucket_sessions,
                self.minimum_scored_sessions,
                self.minimum_positive_windows,
            )
            <= 0
        ):
            raise ValueError("volatility-regime counts must be positive")
        if not Decimal("0") < self.holdout_fraction < Decimal("1"):
            raise ValueError("holdout fraction must be between zero and one")
        if not Decimal("0") < self.minimum_improvement < Decimal("1"):
            raise ValueError("minimum improvement must be between zero and one")


@dataclass(frozen=True, slots=True)
class VolatilityObservation:
    """One valid session's early and later absolute M1 price movement."""

    session_day: date
    predictor: Decimal
    outcome: Decimal


@dataclass(frozen=True, slots=True)
class MovementForecast:
    """One strictly out-of-sample forecast and its observed outcome."""

    session_day: date
    observed: Decimal
    baseline: Decimal
    model: Decimal


@dataclass(frozen=True, slots=True)
class ForecastMetrics:
    """Paired MAE results for the model and its simple benchmark."""

    scored_sessions: int
    baseline_mae: Decimal
    model_mae: Decimal
    improvement: Decimal


@dataclass(frozen=True, slots=True)
class VolatilityGateDecision:
    """Explainable pass/fail decision with no trading authority."""

    passed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VolatilityValidationReport:
    """Frozen-protocol result for the risk-regime research candidate."""

    valid_observations: int
    excluded_sessions: int
    development_metrics: ForecastMetrics
    holdout_metrics: ForecastMetrics
    walk_forward_metrics: tuple[ForecastMetrics, ...]
    gate_decision: VolatilityGateDecision


@dataclass(frozen=True, slots=True)
class _FittedForecaster:
    lower_cutoff: Decimal
    upper_cutoff: Decimal
    baseline: Decimal
    low_forecast: Decimal
    middle_forecast: Decimal
    high_forecast: Decimal

    def forecast(self, predictor: Decimal) -> Decimal:
        if predictor <= self.lower_cutoff:
            return self.low_forecast
        if predictor <= self.upper_cutoff:
            return self.middle_forecast
        return self.high_forecast


def build_volatility_observations(
    bars: Iterable[MinuteBar],
    *,
    settings: VolatilityRegimeSettings,
    excluded_session_days: frozenset[date],
) -> tuple[tuple[VolatilityObservation, ...], int]:
    """Build valid chronological observations without guessing missing M1 data."""
    timezone = ZoneInfo(settings.timezone)
    bars_by_day: dict[date, list[MinuteBar]] = {}
    for bar in bars:
        session_day = bar.timestamp.astimezone(timezone).date()
        if session_day.weekday() < 5:
            bars_by_day.setdefault(session_day, []).append(bar)

    observations: list[VolatilityObservation] = []
    excluded = 0
    for session_day in sorted(bars_by_day):
        if session_day in excluded_session_days:
            excluded += 1
            continue
        observation = _build_observation(
            bars_by_day[session_day], session_day=session_day, settings=settings
        )
        if observation is None:
            excluded += 1
        else:
            observations.append(observation)
    return tuple(observations), excluded


def validate_volatility_regime(
    observations: Sequence[VolatilityObservation],
    *,
    excluded_sessions: int,
    settings: VolatilityRegimeSettings,
) -> VolatilityValidationReport:
    """Apply fixed walk-forward and untouched-holdout forecasting checks."""
    _validate_observations(observations)
    holdout_count = int(
        (Decimal(len(observations)) * settings.holdout_fraction).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    development = tuple(observations[:-holdout_count])
    holdout = tuple(observations[-holdout_count:])
    windows = _walk_forward_windows(development, settings)
    walk_metrics = tuple(
        _score_fitted_forecaster(training, validation, settings)
        for training, validation in windows
    )
    development_metrics = _combine_metrics(walk_metrics)
    holdout_metrics = _score_fitted_forecaster(development, holdout, settings)
    decision = _evaluate_gate(
        development_metrics, holdout_metrics, walk_metrics, settings
    )
    return VolatilityValidationReport(
        valid_observations=len(observations),
        excluded_sessions=excluded_sessions,
        development_metrics=development_metrics,
        holdout_metrics=holdout_metrics,
        walk_forward_metrics=walk_metrics,
        gate_decision=decision,
    )


def _build_observation(
    bars: Iterable[MinuteBar],
    *,
    session_day: date,
    settings: VolatilityRegimeSettings,
) -> VolatilityObservation | None:
    timezone = ZoneInfo(settings.timezone)
    start = datetime.combine(session_day, settings.predictor_start, tzinfo=timezone)
    predictor_end = datetime.combine(
        session_day, settings.predictor_end, tzinfo=timezone
    )
    outcome_end = datetime.combine(session_day, settings.outcome_end, tzinfo=timezone)
    window = complete_minute_window(
        bars, start=start, end=outcome_end - timedelta(minutes=1)
    )
    if window is None:
        return None
    closes = {bar.timestamp.astimezone(timezone): bar.close for bar in window}
    predictor_closes = tuple(
        closes[start + timedelta(minutes=offset)]
        for offset in range(_minutes_between(start, predictor_end))
    )
    outcome_closes = tuple(
        closes[predictor_end + timedelta(minutes=offset)]
        for offset in range(_minutes_between(predictor_end, outcome_end))
    )
    return VolatilityObservation(
        session_day=session_day,
        predictor=_absolute_close_moves(predictor_closes),
        outcome=_absolute_close_moves((predictor_closes[-1], *outcome_closes)),
    )


def _absolute_close_moves(closes: Sequence[Decimal]) -> Decimal:
    if len(closes) < 2:
        raise ValueError("at least two closes are required")
    return sum(
        (
            abs(current - previous)
            for previous, current in zip(closes, closes[1:], strict=False)
        ),
        start=Decimal("0"),
    )


def _walk_forward_windows(
    development: Sequence[VolatilityObservation],
    settings: VolatilityRegimeSettings,
) -> tuple[
    tuple[tuple[VolatilityObservation, ...], tuple[VolatilityObservation, ...]], ...
]:
    windows = []
    start = 0
    while start + settings.training_sessions + settings.validation_sessions <= len(
        development
    ):
        training_end = start + settings.training_sessions
        validation_end = training_end + settings.validation_sessions
        windows.append(
            (
                tuple(development[start:training_end]),
                tuple(development[training_end:validation_end]),
            )
        )
        start += settings.validation_step_sessions
    if not windows:
        raise ValueError(
            "insufficient development sessions for walk-forward validation"
        )
    return tuple(windows)


def _score_fitted_forecaster(
    training: Sequence[VolatilityObservation],
    validation: Sequence[VolatilityObservation],
    settings: VolatilityRegimeSettings,
) -> ForecastMetrics:
    if len(training) < settings.training_sessions:
        raise ValueError("forecast training set is smaller than the configured minimum")
    forecaster = _fit_forecaster(training, settings.minimum_bucket_sessions)
    forecasts = tuple(
        MovementForecast(
            session_day=item.session_day,
            observed=item.outcome,
            baseline=forecaster.baseline,
            model=forecaster.forecast(item.predictor),
        )
        for item in validation
    )
    return _score_forecasts(forecasts)


def _fit_forecaster(
    training: Sequence[VolatilityObservation], minimum_bucket_sessions: int
) -> _FittedForecaster:
    predictors = sorted(item.predictor for item in training)
    lower_cutoff = predictors[(len(predictors) - 1) // 3]
    upper_cutoff = predictors[(2 * (len(predictors) - 1)) // 3]
    baseline = _median(item.outcome for item in training)
    buckets: dict[str, list[Decimal]] = {"low": [], "middle": [], "high": []}
    for item in training:
        bucket = _bucket(item.predictor, lower_cutoff, upper_cutoff)
        buckets[bucket].append(item.outcome)
    return _FittedForecaster(
        lower_cutoff=lower_cutoff,
        upper_cutoff=upper_cutoff,
        baseline=baseline,
        low_forecast=_bucket_median(buckets["low"], baseline, minimum_bucket_sessions),
        middle_forecast=_bucket_median(
            buckets["middle"], baseline, minimum_bucket_sessions
        ),
        high_forecast=_bucket_median(
            buckets["high"], baseline, minimum_bucket_sessions
        ),
    )


def _bucket(value: Decimal, lower_cutoff: Decimal, upper_cutoff: Decimal) -> str:
    if value <= lower_cutoff:
        return "low"
    if value <= upper_cutoff:
        return "middle"
    return "high"


def _bucket_median(
    values: Sequence[Decimal], baseline: Decimal, minimum_sessions: int
) -> Decimal:
    return _median(values) if len(values) >= minimum_sessions else baseline


def _score_forecasts(forecasts: Sequence[MovementForecast]) -> ForecastMetrics:
    if not forecasts:
        raise ValueError("at least one forecast is required")
    baseline_mae = _mean_decimal(
        abs(item.observed - item.baseline) for item in forecasts
    )
    model_mae = _mean_decimal(abs(item.observed - item.model) for item in forecasts)
    if baseline_mae <= 0:
        raise ValueError("baseline MAE must be positive")
    return ForecastMetrics(
        scored_sessions=len(forecasts),
        baseline_mae=baseline_mae,
        model_mae=model_mae,
        improvement=Decimal("1") - model_mae / baseline_mae,
    )


def _combine_metrics(metrics: Sequence[ForecastMetrics]) -> ForecastMetrics:
    if not metrics:
        raise ValueError("at least one walk-forward metric is required")
    total_sessions = sum(item.scored_sessions for item in metrics)
    baseline_mae = (
        sum(
            (item.baseline_mae * item.scored_sessions for item in metrics), Decimal("0")
        )
        / total_sessions
    )
    model_mae = (
        sum((item.model_mae * item.scored_sessions for item in metrics), Decimal("0"))
        / total_sessions
    )
    return ForecastMetrics(
        scored_sessions=total_sessions,
        baseline_mae=baseline_mae,
        model_mae=model_mae,
        improvement=Decimal("1") - model_mae / baseline_mae,
    )


def _evaluate_gate(
    development: ForecastMetrics,
    holdout: ForecastMetrics,
    windows: Sequence[ForecastMetrics],
    settings: VolatilityRegimeSettings,
) -> VolatilityGateDecision:
    reasons: list[str] = []
    if development.scored_sessions < settings.minimum_scored_sessions:
        reasons.append("development has insufficient scored sessions")
    if holdout.scored_sessions < settings.minimum_scored_sessions:
        reasons.append("holdout has insufficient scored sessions")
    if development.improvement < settings.minimum_improvement:
        reasons.append("development MAE improvement is below the required minimum")
    if holdout.improvement < settings.minimum_improvement:
        reasons.append("holdout MAE improvement is below the required minimum")
    positive_windows = sum(
        item.improvement >= settings.minimum_improvement for item in windows
    )
    if positive_windows < settings.minimum_positive_windows:
        reasons.append("insufficient walk-forward windows meet the MAE threshold")
    return VolatilityGateDecision(passed=not reasons, reasons=tuple(reasons))


def _median(values: Iterable[Decimal]) -> Decimal:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("median requires at least one value")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def _mean_decimal(values: Iterable[Decimal]) -> Decimal:
    items = tuple(values)
    if not items:
        raise ValueError("mean requires at least one value")
    return sum(items, start=Decimal("0")) / Decimal(len(items))


def _minutes_between(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def _validate_observations(observations: Sequence[VolatilityObservation]) -> None:
    days = tuple(item.session_day for item in observations)
    if not observations:
        raise ValueError("at least one volatility observation is required")
    if days != tuple(sorted(days)) or len(set(days)) != len(days):
        raise ValueError(
            "volatility observations must have unique ascending session dates"
        )
