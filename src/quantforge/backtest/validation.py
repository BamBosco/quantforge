"""Strategy-neutral chronological validation and promotion-gate calculations."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, Decimal


@dataclass(frozen=True, slots=True)
class ValidationSession:
    """One chronologically ordered research session with optional normalized R."""

    session_day: date
    r_multiple: Decimal | None


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """Non-monetary metrics derived only from completed simulated trades."""

    sessions: int
    completed_trades: int
    wins: int
    losses: int
    total_r: Decimal | None
    mean_r: Decimal | None
    maximum_drawdown_r: Decimal
    profit_factor: Decimal | None


@dataclass(frozen=True, slots=True)
class ChronologicalSplit:
    """Fixed development and untouched holdout portions of a session sequence."""

    development: tuple[ValidationSession, ...]
    holdout: tuple[ValidationSession, ...]


@dataclass(frozen=True, slots=True)
class WalkForwardWindow:
    """One chronological fit/validation window without overlapping information."""

    training: tuple[ValidationSession, ...]
    validation: tuple[ValidationSession, ...]


@dataclass(frozen=True, slots=True)
class CostStressReport:
    """Comparable metrics for identically dated cost scenarios."""

    scenarios: dict[str, PerformanceMetrics]


@dataclass(frozen=True, slots=True)
class ResearchGate:
    """Predeclared historical requirements for confirmation eligibility only."""

    minimum_completed_trades: int
    require_positive_total_r: bool
    require_positive_mean_r: bool
    require_positive_holdout: bool
    minimum_positive_walk_forward_windows: int

    def __post_init__(self) -> None:
        if self.minimum_completed_trades <= 0:
            raise ValueError("minimum completed trades must be positive")
        if self.minimum_positive_walk_forward_windows <= 0:
            raise ValueError("minimum positive walk-forward windows must be positive")


@dataclass(frozen=True, slots=True)
class ResearchGateDecision:
    """Explainable pass/fail result for the historical research gate."""

    passed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResearchValidationReport:
    """Complete strategy-neutral validation output for one fixed experiment."""

    splits: dict[str, ChronologicalSplit]
    walk_forward: dict[str, tuple[WalkForwardWindow, ...]]
    development_cost_stress: CostStressReport
    full_sample_cost_stress: CostStressReport
    gate_decision: ResearchGateDecision


def evaluate_performance(sessions: Sequence[ValidationSession]) -> PerformanceMetrics:
    """Calculate outcome metrics without account-size or leverage assumptions."""
    _validate_order(sessions)
    outcomes = [item.r_multiple for item in sessions if item.r_multiple is not None]
    if not outcomes:
        return PerformanceMetrics(
            sessions=len(sessions),
            completed_trades=0,
            wins=0,
            losses=0,
            total_r=None,
            mean_r=None,
            maximum_drawdown_r=Decimal("0"),
            profit_factor=None,
        )
    total_r = sum(outcomes, start=Decimal("0"))
    gains = sum((value for value in outcomes if value > 0), start=Decimal("0"))
    losses = sum((-value for value in outcomes if value < 0), start=Decimal("0"))
    return PerformanceMetrics(
        sessions=len(sessions),
        completed_trades=len(outcomes),
        wins=sum(value > 0 for value in outcomes),
        losses=sum(value < 0 for value in outcomes),
        total_r=total_r,
        mean_r=total_r / Decimal(len(outcomes)),
        maximum_drawdown_r=_maximum_drawdown(outcomes),
        profit_factor=gains / losses if losses > 0 else None,
    )


def split_chronologically(
    sessions: Sequence[ValidationSession], *, holdout_fraction: Decimal
) -> ChronologicalSplit:
    """Reserve the final contiguous fraction of sessions as untouched holdout."""
    _validate_order(sessions)
    if not Decimal("0") < holdout_fraction < Decimal("1"):
        raise ValueError("holdout fraction must be greater than zero and less than one")
    holdout_count = int(
        (Decimal(len(sessions)) * holdout_fraction).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    development_count = len(sessions) - holdout_count
    if development_count <= 0 or holdout_count <= 0:
        raise ValueError(
            "chronological split requires development and holdout sessions"
        )
    return ChronologicalSplit(
        development=tuple(sessions[:development_count]),
        holdout=tuple(sessions[development_count:]),
    )


def build_walk_forward_windows(
    sessions: Sequence[ValidationSession],
    *,
    training_sessions: int,
    validation_sessions: int,
    step_sessions: int,
    maximum_windows: int | None = None,
) -> tuple[WalkForwardWindow, ...]:
    """Build fixed chronological windows without crossing future boundaries."""
    _validate_order(sessions)
    if min(training_sessions, validation_sessions, step_sessions) <= 0:
        raise ValueError("walk-forward window sizes must be positive")
    if maximum_windows is not None and maximum_windows <= 0:
        raise ValueError("maximum walk-forward windows must be positive")
    windows: list[WalkForwardWindow] = []
    start = 0
    while start + training_sessions + validation_sessions <= len(sessions):
        training_end = start + training_sessions
        validation_end = training_end + validation_sessions
        windows.append(
            WalkForwardWindow(
                training=tuple(sessions[start:training_end]),
                validation=tuple(sessions[training_end:validation_end]),
            )
        )
        if maximum_windows is not None and len(windows) >= maximum_windows:
            break
        start += step_sessions
    if not windows:
        raise ValueError("insufficient sessions for one walk-forward window")
    return tuple(windows)


def evaluate_cost_stress(
    scenarios: Mapping[str, Sequence[ValidationSession]],
) -> CostStressReport:
    """Reject cost scenarios that do not evaluate the exact same session dates."""
    if not scenarios:
        raise ValueError("at least one cost scenario is required")
    expected_dates: tuple[date, ...] | None = None
    metrics: dict[str, PerformanceMetrics] = {}
    for name, sessions in scenarios.items():
        if not name:
            raise ValueError("cost scenario name must not be empty")
        _validate_order(sessions)
        dates = tuple(item.session_day for item in sessions)
        if expected_dates is None:
            expected_dates = dates
        elif dates != expected_dates:
            raise ValueError("cost scenarios must have identical session dates")
        metrics[name] = evaluate_performance(sessions)
    return CostStressReport(scenarios=metrics)


def run_research_validation(
    scenarios: Mapping[str, Sequence[ValidationSession]],
    *,
    holdout_fraction: Decimal,
    training_sessions: int,
    validation_sessions: int,
    step_sessions: int,
    gate: ResearchGate,
    maximum_walk_forward_windows: int | None = None,
) -> ResearchValidationReport:
    """Apply one fixed chronological protocol to every cost scenario equally."""
    full_sample_cost_stress = evaluate_cost_stress(scenarios)
    splits = {
        name: split_chronologically(sessions, holdout_fraction=holdout_fraction)
        for name, sessions in scenarios.items()
    }
    walk_forward = {
        name: build_walk_forward_windows(
            split.development,
            training_sessions=training_sessions,
            validation_sessions=validation_sessions,
            step_sessions=step_sessions,
            maximum_windows=maximum_walk_forward_windows,
        )
        for name, split in splits.items()
    }
    development_cost_stress = evaluate_cost_stress(
        {name: split.development for name, split in splits.items()}
    )
    gate_decision = evaluate_research_gate(
        gate=gate,
        holdout_by_scenario={
            name: evaluate_performance(split.holdout) for name, split in splits.items()
        },
        cost_stress=development_cost_stress,
        walk_forward_by_scenario=walk_forward,
    )
    return ResearchValidationReport(
        splits=splits,
        walk_forward=walk_forward,
        development_cost_stress=development_cost_stress,
        full_sample_cost_stress=full_sample_cost_stress,
        gate_decision=gate_decision,
    )


def evaluate_research_gate(
    *,
    gate: ResearchGate,
    holdout_by_scenario: Mapping[str, PerformanceMetrics],
    cost_stress: CostStressReport,
    walk_forward_by_scenario: Mapping[str, Sequence[WalkForwardWindow]],
) -> ResearchGateDecision:
    """Evaluate predeclared criteria; a pass permits confirmation only."""
    reasons: list[str] = []
    if not holdout_by_scenario or not walk_forward_by_scenario:
        raise ValueError("holdout and walk-forward results are required")
    for name, windows in walk_forward_by_scenario.items():
        positive_windows = sum(
            _is_positive(evaluate_performance(window.validation)) for window in windows
        )
        if positive_windows < gate.minimum_positive_walk_forward_windows:
            reasons.append(f"{name}: insufficient positive walk-forward windows")
    for name, holdout in holdout_by_scenario.items():
        if gate.require_positive_holdout and not _is_positive(holdout):
            reasons.append(f"{name}: holdout total or mean R is not positive")
    for name, metrics in cost_stress.scenarios.items():
        if metrics.completed_trades < gate.minimum_completed_trades:
            reasons.append(f"{name}: insufficient completed trades")
        if gate.require_positive_total_r and not _is_positive_total(metrics):
            reasons.append(f"{name}: total R is not positive")
        if gate.require_positive_mean_r and not _is_positive_mean(metrics):
            reasons.append(f"{name}: mean R is not positive")
    return ResearchGateDecision(passed=not reasons, reasons=tuple(reasons))


def _maximum_drawdown(outcomes: Sequence[Decimal]) -> Decimal:
    """Return the largest peak-to-trough loss in cumulative normalized R."""
    cumulative = Decimal("0")
    peak = Decimal("0")
    maximum_drawdown = Decimal("0")
    for outcome in outcomes:
        cumulative += outcome
        peak = max(peak, cumulative)
        maximum_drawdown = max(maximum_drawdown, peak - cumulative)
    return maximum_drawdown


def _is_positive(metrics: PerformanceMetrics) -> bool:
    return _is_positive_total(metrics) and _is_positive_mean(metrics)


def _is_positive_total(metrics: PerformanceMetrics) -> bool:
    return metrics.total_r is not None and metrics.total_r > 0


def _is_positive_mean(metrics: PerformanceMetrics) -> bool:
    return metrics.mean_r is not None and metrics.mean_r > 0


def _validate_order(sessions: Sequence[ValidationSession]) -> None:
    """Require unique, ascending session dates before any chronology calculation."""
    days = tuple(item.session_day for item in sessions)
    if not days:
        raise ValueError("at least one validation session is required")
    if days != tuple(sorted(days)) or len(set(days)) != len(days):
        raise ValueError("validation sessions must have unique ascending session dates")
