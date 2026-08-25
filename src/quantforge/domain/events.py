"""Versioned immutable workflow messages.

These contracts intentionally distinguish a strategy's non-executable intent
from the Risk Engine's executable approval.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for a newly created event."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Base metadata required for all durable domain events."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=utc_now)
    correlation_id: UUID = field(default_factory=uuid4)
    causation_id: UUID | None = None
    schema_version: int = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class TradeIntentGenerated(DomainEvent):
    """A strategy proposal with no executable quantity."""

    strategy_id: str
    instrument: str
    side: str
    entry_price: Decimal
    stop_loss_price: Decimal
    target_price: Decimal | None = None
    scheduled_exit_at: datetime | None = None
    rationale: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderApproved(DomainEvent):
    """An executable instruction issued only after a risk decision."""

    intent_id: UUID
    decision_id: UUID
    policy_version: str
    instrument: str
    side: str
    quantity: Decimal
    expires_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class RiskDecisionRecorded(DomainEvent):
    """The auditable, risk-owned result of evaluating one trade intent."""

    intent_id: UUID
    approved: bool
    policy_version: str
    reasons: tuple[str, ...]
    quantity: Decimal | None = None
    proposed_risk: Decimal | None = None
    kill_switch_required: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionOutcomeRecorded(DomainEvent):
    """A paper or venue execution outcome linked to an approved order."""

    order_id: UUID
    status: str
    instrument: str
    side: str
    quantity: Decimal
    price: Decimal | None
    reason: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class EventRiskDecisionRecorded(DomainEvent):
    """An auditable scheduled-event decision produced by the Risk Engine."""

    instrument: str
    policy_id: str
    policy_version: str
    calendar_snapshot_id: str
    actions: tuple[str, ...]
    reason: str
    provider_event_id: str | None = None
    blackout_starts_at: datetime | None = None
