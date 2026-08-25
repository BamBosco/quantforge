"""Research-mode pre-trade validation shared by backtests and execution."""

from dataclasses import dataclass
from decimal import Decimal

from quantforge.risk.event_policy import EventRiskDecision


@dataclass(frozen=True, slots=True)
class IntentValidation:
    """A non-bypassable record of whether a proposed trade has valid risk shape."""

    approved: bool
    reasons: tuple[str, ...]


def validate_protective_stop(
    side: str, entry: Decimal, stop: Decimal
) -> IntentValidation:
    """Reject trade shapes without a loss-limiting protective stop."""
    if entry <= 0 or stop <= 0:
        return IntentValidation(False, ("entry and stop must be positive",))
    if side == "buy" and stop >= entry:
        return IntentValidation(False, ("buy stop must be below entry",))
    if side == "sell" and stop <= entry:
        return IntentValidation(False, ("sell stop must be above entry",))
    if side not in {"buy", "sell"}:
        return IntentValidation(False, ("side must be buy or sell",))
    return IntentValidation(True, ())


def validate_event_risk(decision: EventRiskDecision) -> IntentValidation:
    """Reject an entry intent whenever the event-risk policy blocks it."""
    if decision.allows_new_intents:
        return IntentValidation(True, ())
    return IntentValidation(False, (f"event-risk policy: {decision.reason}",))
