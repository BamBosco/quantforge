"""Deterministic reconciliation for paper order and position state."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from quantforge.execution.conditional_orders import PendingOrderStatus
from quantforge.portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class PaperOrderState:
    order_id: UUID
    instrument: str
    side: str
    quantity: Decimal
    stop_loss_price: Decimal
    target_price: Decimal | None
    status: str

    @property
    def signed_quantity(self) -> Decimal:
        return self.quantity if self.side == "buy" else -self.quantity


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    matched: bool
    reasons: tuple[str, ...]


def reconcile_pending_orders(
    expected: Mapping[UUID, PendingOrderStatus],
    actual: Mapping[UUID, PendingOrderStatus],
) -> ReconciliationResult:
    """Compare externally expected pending-order lifecycle state to paper state."""
    reasons = tuple(
        f"pending order mismatch for {order_id}: expected {expected.get(order_id)}, "
        f"actual {actual.get(order_id)}"
        for order_id in sorted(set(expected) | set(actual), key=str)
        if expected.get(order_id) != actual.get(order_id)
    )
    return ReconciliationResult(not reasons, reasons)


def reconcile_paper_state(
    orders: Mapping[UUID, PaperOrderState], portfolio: Portfolio
) -> ReconciliationResult:
    """Compare open paper orders with portfolio positions, fail-closed on drift."""
    expected: dict[str, Decimal] = {}
    for order in orders.values():
        if order.status == "filled":
            expected[order.instrument] = (
                expected.get(order.instrument, Decimal("0")) + order.signed_quantity
            )
    actual = {
        instrument: position.quantity
        for instrument, position in portfolio.positions.items()
    }
    reasons: list[str] = []
    for instrument in sorted(set(expected) | set(actual)):
        expected_quantity = expected.get(instrument, Decimal("0"))
        actual_quantity = actual.get(instrument, Decimal("0"))
        if expected_quantity != actual_quantity:
            reasons.append(
                f"position mismatch for {instrument}: expected {expected_quantity}, "
                f"actual {actual_quantity}"
            )
    return ReconciliationResult(not reasons, tuple(reasons))
