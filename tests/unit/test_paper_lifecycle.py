"""Parity fixtures for the generic paper conditional-order lifecycle."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from quantforge.domain.events import OrderApproved, TradeIntentGenerated
from quantforge.execution import (
    PaperExecutor,
    PendingOrderStatus,
    PendingStopEntry,
    Quote,
    reconcile_pending_orders,
)
from quantforge.journal import SQLiteEventJournal
from quantforge.portfolio import Portfolio
from quantforge.risk.event_policy import EventRiskAction, EventRiskDecision

NOW = datetime(2026, 8, 20, 12, tzinfo=UTC)


def _pending(side: str, trigger: str, group_id: UUID) -> PendingStopEntry:
    intent = TradeIntentGenerated(
        strategy_id="approved_future_strategy",
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
        expires_at=NOW + timedelta(minutes=5),
    )
    return PendingStopEntry(order, intent, Decimal(trigger), group_id)


def test_pending_oco_trigger_journals_then_fills_and_cancels_peer(
    tmp_path: Path,
) -> None:
    journal = SQLiteEventJournal(tmp_path / "paper.sqlite3")
    executor = PaperExecutor(Portfolio(Decimal("10000")), journal=journal)
    group_id = uuid4()
    buy = _pending("buy", "101", group_id)
    sell = _pending("sell", "99", group_id)
    executor.place_pending_stop(buy)
    executor.place_pending_stop(sell)

    fills = executor.process_pending_quote(
        Quote("XAUUSD", Decimal("100.9"), Decimal("101"), NOW)
    )

    assert fills[0].outcome.status == "filled"
    assert (
        executor.pending_statuses()[sell.order.event_id] is PendingOrderStatus.CANCELED
    )
    assert executor.reconcile_pending(executor.pending_statuses()).matched
    assert executor.reconcile().matched
    assert [json.loads(event["payload_json"])["status"] for event in journal.events()][
        -3:
    ] == [
        "triggered",
        "canceled",
        "filled",
    ]
    journal.close()


def test_scheduled_exit_and_event_blackout_flatten_open_positions() -> None:
    executor = PaperExecutor(Portfolio(Decimal("10000")))
    pending = _pending("buy", "101", uuid4())
    executor.place_pending_stop(pending)
    executor.process_pending_quote(
        Quote("XAUUSD", Decimal("100.9"), Decimal("101"), NOW)
    )
    executor.schedule_exit(pending.order.event_id, exit_at=NOW)

    scheduled = executor.process_scheduled_exits(
        evaluated_at=NOW,
        quotes={"XAUUSD": Quote("XAUUSD", Decimal("100"), Decimal("100.1"), NOW)},
    )

    assert scheduled[0].outcome.status == "forced_exit"

    executor = PaperExecutor(Portfolio(Decimal("10000")))
    open_pending = _pending("buy", "101", uuid4())
    blocked_pending = _pending("sell", "99", uuid4())
    executor.place_pending_stop(open_pending)
    executor.place_pending_stop(blocked_pending)
    executor.process_pending_quote(
        Quote("XAUUSD", Decimal("100.9"), Decimal("101"), NOW)
    )
    decision = EventRiskDecision(
        instrument="XAUUSD",
        policy_id="test",
        policy_version="1",
        calendar_snapshot_id="test",
        actions=frozenset(
            {
                EventRiskAction.CANCEL_PENDING_ENTRIES,
                EventRiskAction.FLATTEN_OPEN_POSITION,
            }
        ),
        reason="test blackout",
    )

    flattened = executor.apply_event_risk(
        decision,
        quotes={"XAUUSD": Quote("XAUUSD", Decimal("100"), Decimal("100.1"), NOW)},
    )

    assert flattened[0].outcome.status == "event_flattened"
    assert (
        executor.pending_statuses()[blocked_pending.order.event_id]
        is PendingOrderStatus.CANCELED
    )


def test_pending_reconciliation_reports_state_drift() -> None:
    order_id = uuid4()

    result = reconcile_pending_orders(
        {order_id: PendingOrderStatus.PENDING},
        {order_id: PendingOrderStatus.CANCELED},
    )

    assert not result.matched
    assert "pending order mismatch" in result.reasons[0]
