from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from quantforge.domain.events import OrderApproved, TradeIntentGenerated


def test_trade_intent_carries_no_executable_quantity() -> None:
    intent = TradeIntentGenerated(
        strategy_id="example",
        instrument="EURUSD",
        side="buy",
        entry_price=Decimal("1.08000"),
        stop_loss_price=Decimal("1.07500"),
    )

    assert not hasattr(intent, "quantity")


def test_approved_order_requires_risk_decision_traceability() -> None:
    order = OrderApproved(
        intent_id=uuid4(),
        decision_id=uuid4(),
        policy_version="0.1",
        instrument="EURUSD",
        side="buy",
        quantity=Decimal("0.10"),
        expires_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )

    assert order.policy_version == "0.1"
