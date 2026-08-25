"""Summary metrics for research runs; intentionally limited to normalized R."""

from dataclasses import dataclass
from decimal import Decimal

from quantforge.backtest.orb_runner import OrbBacktestRun
from quantforge.backtest.orb_simulation import SessionOutcome
from quantforge.backtest.validation import (
    ValidationSession,
    evaluate_performance,
)


@dataclass(frozen=True, slots=True)
class OrbBacktestSummary:
    """Non-monetary summary that keeps ambiguous outcomes out of trade metrics."""

    evaluated_sessions: int
    skipped_sessions: int
    completed_trades: int
    ambiguous_sessions: int
    total_r: Decimal | None
    mean_r: Decimal | None
    outcome_counts: dict[SessionOutcome, int]


def summarize_orb_backtest(run: OrbBacktestRun) -> OrbBacktestSummary:
    """Summarize only completed fills; no capital or position-size assumptions exist."""
    metrics = evaluate_performance(to_validation_sessions(run))
    outcome_counts = {
        outcome: sum(result.outcome is outcome for result in run.results)
        for outcome in SessionOutcome
    }
    return OrbBacktestSummary(
        evaluated_sessions=len(run.results),
        skipped_sessions=len(run.skipped_sessions),
        completed_trades=metrics.completed_trades,
        ambiguous_sessions=outcome_counts[SessionOutcome.AMBIGUOUS],
        total_r=metrics.total_r,
        mean_r=metrics.mean_r,
        outcome_counts=outcome_counts,
    )


def to_validation_sessions(run: OrbBacktestRun) -> tuple[ValidationSession, ...]:
    """Adapt one strategy's non-sized results to the generic validation contract."""
    return tuple(
        ValidationSession(result.session_day, result.r_multiple)
        for result in run.results
    )
