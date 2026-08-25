"""Tests for strategy-neutral pending stops, OCO, and risk reservations."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from quantforge.domain.events import OrderApproved, TradeIntentGenerated
from quantforge.execution import (
    ConditionalOrderBook,
    PendingOrderStatus,
    PendingStopEntry,
    Quote,
)
from quantforge.risk import ConditionalRiskReservations

NOW = datetime(2026, 8, 20, 12, tzinfo=UTC)


def _entry(side: str, trigger: str, group_id: UUID) -> PendingStopEntry:
    intent = TradeIntentGenerated(
        strategy_id="future_candidate",
        instrument="XAUUSD",
        side=side,
        entry_price=Decimal(trigger),
        stop_loss_price=Decimal("99") if side == "buy" else Decimal("101"),
    )
    order = OrderApproved(
        intent_id=intent.event_id,
        decision_id=uuid4(),
        policy_version="paper-0.1",
        instrument="XAUUSD",
        side=side,
        quantity=Decimal("1"),
        expires_at=NOW + timedelta(minutes=1),
    )
    return PendingStopEntry(order, intent, Decimal(trigger), group_id)


def test_first_oco_stop_trigger_cancels_its_peer() -> None:
    group_id = uuid4()
    buy = _entry("buy", "101", group_id)
    sell = _entry("sell", "99", group_id)
    book = ConditionalOrderBook()
    book.place(buy)
    book.place(sell)

    transitions = book.process_quote(
        Quote("XAUUSD", Decimal("100.9"), Decimal("101"), NOW)
    )

    assert [transition.status for transition in transitions] == [
        PendingOrderStatus.TRIGGERED,
        PendingOrderStatus.CANCELED,
    ]
    assert book.status(buy.order.event_id) is PendingOrderStatus.TRIGGERED
    assert book.status(sell.order.event_id) is PendingOrderStatus.CANCELED


def test_same_observation_oco_trigger_is_ambiguous() -> None:
    group_id = uuid4()
    buy = _entry("buy", "101", group_id)
    sell = _entry("sell", "99", group_id)
    book = ConditionalOrderBook()
    book.place(buy)
    book.place(sell)

    transitions = book.process_quote(
        Quote("XAUUSD", Decimal("99"), Decimal("101"), NOW)
    )

    assert all(
        transition.status is PendingOrderStatus.AMBIGUOUS for transition in transitions
    )


def test_oco_reserves_only_the_larger_side_risk() -> None:
    reservations = ConditionalRiskReservations()
    reservation = reservations.reserve_oco(
        uuid4(), {uuid4(): Decimal("80"), uuid4(): Decimal("100")}
    )

    assert reservation.reserved_risk == Decimal("100")
    assert reservations.total_reserved_risk == Decimal("100")
