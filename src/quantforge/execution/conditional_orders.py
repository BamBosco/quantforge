"""Strategy-neutral conditional stop-entry and OCO state management."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from quantforge.domain.events import (
    ExecutionOutcomeRecorded,
    OrderApproved,
    TradeIntentGenerated,
)
from quantforge.execution.models import Quote
from quantforge.journal.sqlite import SQLiteEventJournal


class PendingOrderStatus(StrEnum):
    PENDING = "pending"
    TRIGGERED = "triggered"
    CANCELED = "canceled"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class PendingStopEntry:
    """One risk-approved stop entry, optionally belonging to an OCO group."""

    order: OrderApproved
    intent: TradeIntentGenerated
    trigger_price: Decimal
    oco_group_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.order.intent_id != self.intent.event_id:
            raise ValueError("pending entry order must reference its trade intent")
        if (
            self.order.instrument != self.intent.instrument
            or self.order.side != self.intent.side
        ):
            raise ValueError("pending entry order and intent must match")
        if self.trigger_price <= 0:
            raise ValueError("stop trigger price must be positive")


@dataclass(frozen=True, slots=True)
class PendingOrderTransition:
    order_id: UUID
    status: PendingOrderStatus
    reason: str


class ConditionalOrderBook:
    """Deterministic conditional-order state; it does not execute a broker order."""

    def __init__(self, *, journal: SQLiteEventJournal | None = None) -> None:
        self._entries: dict[UUID, PendingStopEntry] = {}
        self._statuses: dict[UUID, PendingOrderStatus] = {}
        self._journal = journal

    def place(self, entry: PendingStopEntry) -> PendingOrderTransition:
        if entry.order.event_id in self._entries:
            raise ValueError("conditional order ID must be unique")
        self._entries[entry.order.event_id] = entry
        self._statuses[entry.order.event_id] = PendingOrderStatus.PENDING
        transition = PendingOrderTransition(
            entry.order.event_id,
            PendingOrderStatus.PENDING,
            "conditional entry accepted",
        )
        self._journal_transition(transition)
        return transition

    def cancel(self, order_id: UUID, *, reason: str) -> PendingOrderTransition:
        if self._statuses.get(order_id) is not PendingOrderStatus.PENDING:
            raise ValueError("only pending conditional orders may be canceled")
        self._statuses[order_id] = PendingOrderStatus.CANCELED
        transition = PendingOrderTransition(
            order_id, PendingOrderStatus.CANCELED, reason
        )
        self._journal_transition(transition)
        return transition

    def process_quote(self, quote: Quote) -> tuple[PendingOrderTransition, ...]:
        """Trigger one OCO side or mark simultaneous group triggers ambiguous."""
        candidates = tuple(
            entry
            for order_id, entry in self._entries.items()
            if self._statuses[order_id] is PendingOrderStatus.PENDING
            and entry.order.instrument == quote.instrument
            and self._is_triggered(entry, quote)
        )
        if not candidates:
            return ()
        transitions: list[PendingOrderTransition] = []
        grouped: dict[UUID | None, list[PendingStopEntry]] = {}
        for entry in candidates:
            grouped.setdefault(entry.oco_group_id, []).append(entry)
        for group_id, entries in grouped.items():
            if group_id is not None and len(entries) > 1:
                for entry in entries:
                    self._statuses[entry.order.event_id] = PendingOrderStatus.AMBIGUOUS
                    transitions.append(
                        PendingOrderTransition(
                            entry.order.event_id,
                            PendingOrderStatus.AMBIGUOUS,
                            "multiple OCO entries triggered in one observation",
                        )
                    )
                    self._journal_transition(transitions[-1])
                continue
            entry = entries[0]
            self._statuses[entry.order.event_id] = PendingOrderStatus.TRIGGERED
            transitions.append(
                PendingOrderTransition(
                    entry.order.event_id,
                    PendingOrderStatus.TRIGGERED,
                    "stop trigger reached",
                )
            )
            self._journal_transition(transitions[-1])
            if group_id is not None:
                transitions.extend(self._cancel_oco_peers(entry, group_id))
        return tuple(transitions)

    def status(self, order_id: UUID) -> PendingOrderStatus:
        return self._statuses[order_id]

    def entry(self, order_id: UUID) -> PendingStopEntry:
        return self._entries[order_id]

    def statuses(self) -> dict[UUID, PendingOrderStatus]:
        return dict(self._statuses)

    @staticmethod
    def _is_triggered(entry: PendingStopEntry, quote: Quote) -> bool:
        if quote.bid <= 0 or quote.ask < quote.bid:
            return False
        return (
            quote.ask >= entry.trigger_price
            if entry.order.side == "buy"
            else quote.bid <= entry.trigger_price
        )

    def _cancel_oco_peers(
        self, triggered: PendingStopEntry, group_id: UUID
    ) -> tuple[PendingOrderTransition, ...]:
        transitions: list[PendingOrderTransition] = []
        for order_id, entry in self._entries.items():
            if (
                entry.oco_group_id == group_id
                and order_id != triggered.order.event_id
                and self._statuses[order_id] is PendingOrderStatus.PENDING
            ):
                self._statuses[order_id] = PendingOrderStatus.CANCELED
                transitions.append(
                    PendingOrderTransition(
                        order_id, PendingOrderStatus.CANCELED, "OCO peer triggered"
                    )
                )
                self._journal_transition(transitions[-1])
        return tuple(transitions)

    def _journal_transition(self, transition: PendingOrderTransition) -> None:
        if self._journal is None:
            return
        entry = self._entries[transition.order_id]
        self._journal.append(
            ExecutionOutcomeRecorded(
                correlation_id=entry.order.correlation_id,
                causation_id=entry.order.event_id,
                order_id=entry.order.event_id,
                status=transition.status.value,
                instrument=entry.order.instrument,
                side=entry.order.side,
                quantity=entry.order.quantity,
                price=None,
                reason=transition.reason,
            )
        )
