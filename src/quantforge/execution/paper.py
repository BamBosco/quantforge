"""Deterministic paper executor with no broker or MT5 dependency."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from quantforge.domain.events import (
    ExecutionOutcomeRecorded,
    OrderApproved,
    TradeIntentGenerated,
)
from quantforge.execution.conditional_orders import (
    ConditionalOrderBook,
    PendingOrderStatus,
    PendingStopEntry,
)
from quantforge.execution.models import Quote
from quantforge.execution.reconciliation import (
    PaperOrderState,
    ReconciliationResult,
    reconcile_paper_state,
    reconcile_pending_orders,
)
from quantforge.journal.sqlite import SQLiteEventJournal
from quantforge.portfolio import Fill, Portfolio
from quantforge.risk.event_policy import EventRiskAction, EventRiskDecision
from quantforge.risk.validation import validate_protective_stop


@dataclass(frozen=True, slots=True)
class PaperExecutionResult:
    outcome: ExecutionOutcomeRecorded
    fill: Fill | None


class PaperExecutor:
    """Execute approved orders against an explicit quote in memory only."""

    def __init__(
        self, portfolio: Portfolio, *, journal: SQLiteEventJournal | None = None
    ) -> None:
        self._portfolio = portfolio
        self._journal = journal
        self._submitted_order_ids: set[UUID] = set()
        self._orders: dict[UUID, PaperOrderState] = {}
        self._conditional_orders = ConditionalOrderBook(journal=journal)
        self._scheduled_exits: dict[UUID, datetime] = {}

    def place_pending_stop(self, entry: PendingStopEntry) -> None:
        """Register a risk-approved conditional entry without filling it."""
        self._conditional_orders.place(entry)

    def process_pending_quote(self, quote: Quote) -> tuple[PaperExecutionResult, ...]:
        """Submit triggered conditional entries using the current executable quote."""
        results: list[PaperExecutionResult] = []
        for transition in self._conditional_orders.process_quote(quote):
            if transition.status is PendingOrderStatus.TRIGGERED:
                entry = self._conditional_orders.entry(transition.order_id)
                results.append(
                    self.submit(
                        entry.order,
                        entry.intent,
                        quote=quote,
                        submitted_at=quote.observed_at,
                    )
                )
        return tuple(results)

    def submit(
        self,
        order: OrderApproved,
        intent: TradeIntentGenerated,
        *,
        quote: Quote,
        submitted_at: datetime,
    ) -> PaperExecutionResult:
        """Fill a valid approved order at the adverse side of the current quote."""
        now = submitted_at.astimezone(UTC)
        if order.event_id in self._submitted_order_ids:
            return self._rejected(order, "duplicate paper execution request")
        self._submitted_order_ids.add(order.event_id)
        if now >= order.expires_at.astimezone(UTC):
            return self._rejected(order, "approved order has expired")
        if order.intent_id != intent.event_id:
            return self._rejected(order, "approved order does not match trade intent")
        if order.instrument != intent.instrument or order.side != intent.side:
            return self._rejected(
                order, "approved order fields do not match trade intent"
            )
        stop = validate_protective_stop(
            intent.side, intent.entry_price, intent.stop_loss_price
        )
        if not stop.approved:
            return self._rejected(order, "; ".join(stop.reasons))
        if (
            quote.instrument != order.instrument
            or quote.bid <= 0
            or quote.ask < quote.bid
        ):
            return self._rejected(order, "quote is unavailable or incompatible")
        fill_price = quote.ask if order.side == "buy" else quote.bid
        fill = Fill(order.instrument, order.side, order.quantity, fill_price)
        self._portfolio.apply_fill(fill)
        self._orders[order.event_id] = PaperOrderState(
            order_id=order.event_id,
            instrument=order.instrument,
            side=order.side,
            quantity=order.quantity,
            stop_loss_price=intent.stop_loss_price,
            target_price=intent.target_price,
            status="filled",
        )
        outcome = ExecutionOutcomeRecorded(
            correlation_id=order.correlation_id,
            causation_id=order.event_id,
            order_id=order.event_id,
            status="filled",
            instrument=order.instrument,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
        )
        if self._journal is not None:
            self._journal.append(outcome)
        return PaperExecutionResult(outcome, fill)

    def process_quote(self, quote: Quote) -> tuple[PaperExecutionResult, ...]:
        """Apply stop-loss or target exits using executable bid/ask prices."""
        results: list[PaperExecutionResult] = []
        for order in tuple(self._orders.values()):
            if order.status != "filled" or order.instrument != quote.instrument:
                continue
            status = self._exit_status(order, quote)
            if status is None:
                continue
            exit_side = "sell" if order.side == "buy" else "buy"
            exit_price = quote.bid if exit_side == "sell" else quote.ask
            fill = Fill(order.instrument, exit_side, order.quantity, exit_price)
            self._portfolio.apply_fill(fill)
            self._orders[order.order_id] = PaperOrderState(
                order_id=order.order_id,
                instrument=order.instrument,
                side=order.side,
                quantity=order.quantity,
                stop_loss_price=order.stop_loss_price,
                target_price=order.target_price,
                status=status,
            )
            outcome = ExecutionOutcomeRecorded(
                order_id=order.order_id,
                status=status,
                instrument=order.instrument,
                side=exit_side,
                quantity=order.quantity,
                price=exit_price,
                reason="paper protective exit",
            )
            if self._journal is not None:
                self._journal.append(outcome)
            results.append(PaperExecutionResult(outcome, fill))
        return tuple(results)

    def reconcile(self) -> ReconciliationResult:
        """Compare open paper order state to its portfolio projection."""
        return reconcile_paper_state(self._orders, self._portfolio)

    def pending_statuses(self) -> dict[UUID, PendingOrderStatus]:
        """Return a copy suitable for reconciliation with an external projection."""
        return self._conditional_orders.statuses()

    def reconcile_pending(
        self, expected: dict[UUID, PendingOrderStatus]
    ) -> ReconciliationResult:
        """Compare an external pending-order projection to paper lifecycle state."""
        return reconcile_pending_orders(expected, self.pending_statuses())

    def schedule_exit(self, order_id: UUID, *, exit_at: datetime) -> None:
        """Schedule a generic time-based close for an open paper position."""
        if self._orders.get(order_id, None) is None:
            raise ValueError("cannot schedule an exit for an unknown order")
        if exit_at.tzinfo is None or exit_at.utcoffset() is None:
            raise ValueError("scheduled exit must be timezone-aware")
        self._scheduled_exits[order_id] = exit_at.astimezone(UTC)

    def process_scheduled_exits(
        self, *, evaluated_at: datetime, quotes: dict[str, Quote]
    ) -> tuple[PaperExecutionResult, ...]:
        """Close due positions at current executable, never fabricated, prices."""
        now = evaluated_at.astimezone(UTC)
        results: list[PaperExecutionResult] = []
        for order_id, exit_at in tuple(self._scheduled_exits.items()):
            order = self._orders.get(order_id)
            if now < exit_at or order is None or order.status != "filled":
                continue
            quote = quotes.get(order.instrument)
            if quote is None:
                continue
            results.append(
                self._close_order(order, quote, "forced_exit", "scheduled exit")
            )
            del self._scheduled_exits[order_id]
        return tuple(results)

    def apply_event_risk(
        self, decision: EventRiskDecision, *, quotes: dict[str, Quote]
    ) -> tuple[PaperExecutionResult, ...]:
        """Apply risk-owned cancellation/flatten actions to paper state."""
        if EventRiskAction.CANCEL_PENDING_ENTRIES in decision.actions:
            for order_id, status in self._conditional_orders.statuses().items():
                entry = self._conditional_orders.entry(order_id)
                if (
                    status is PendingOrderStatus.PENDING
                    and entry.order.instrument == decision.instrument
                ):
                    self._conditional_orders.cancel(order_id, reason=decision.reason)
        if EventRiskAction.FLATTEN_OPEN_POSITION not in decision.actions:
            return ()
        quote = quotes.get(decision.instrument)
        if quote is None:
            return ()
        return tuple(
            self._close_order(order, quote, "event_flattened", decision.reason)
            for order in tuple(self._orders.values())
            if order.status == "filled" and order.instrument == decision.instrument
        )

    @staticmethod
    def _exit_status(order: PaperOrderState, quote: Quote) -> str | None:
        if quote.bid <= 0 or quote.ask < quote.bid:
            return None
        if order.side == "buy":
            if quote.bid <= order.stop_loss_price:
                return "stopped_out"
            if order.target_price is not None and quote.bid >= order.target_price:
                return "target_reached"
        else:
            if quote.ask >= order.stop_loss_price:
                return "stopped_out"
            if order.target_price is not None and quote.ask <= order.target_price:
                return "target_reached"
        return None

    def _close_order(
        self, order: PaperOrderState, quote: Quote, status: str, reason: str
    ) -> PaperExecutionResult:
        exit_side = "sell" if order.side == "buy" else "buy"
        exit_price = quote.bid if exit_side == "sell" else quote.ask
        fill = Fill(order.instrument, exit_side, order.quantity, exit_price)
        self._portfolio.apply_fill(fill)
        self._orders[order.order_id] = PaperOrderState(
            order_id=order.order_id,
            instrument=order.instrument,
            side=order.side,
            quantity=order.quantity,
            stop_loss_price=order.stop_loss_price,
            target_price=order.target_price,
            status=status,
        )
        outcome = ExecutionOutcomeRecorded(
            order_id=order.order_id,
            status=status,
            instrument=order.instrument,
            side=exit_side,
            quantity=order.quantity,
            price=exit_price,
            reason=reason,
        )
        if self._journal is not None:
            self._journal.append(outcome)
        return PaperExecutionResult(outcome, fill)

    def _rejected(self, order: OrderApproved, reason: str) -> PaperExecutionResult:
        outcome = ExecutionOutcomeRecorded(
            correlation_id=order.correlation_id,
            causation_id=order.event_id,
            order_id=order.event_id,
            status="rejected",
            instrument=order.instrument,
            side=order.side,
            quantity=order.quantity,
            price=None,
            reason=reason,
        )
        if self._journal is not None:
            self._journal.append(outcome)
        return PaperExecutionResult(outcome, None)
