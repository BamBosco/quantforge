from decimal import Decimal

from quantforge.application.event_bus import EventBus
from quantforge.domain.events import TradeIntentGenerated


def test_dispatches_to_exact_type_subscriber() -> None:
    received: list[TradeIntentGenerated] = []
    bus = EventBus()
    bus.subscribe(TradeIntentGenerated, received.append)
    intent = TradeIntentGenerated(
        strategy_id="example",
        instrument="EURUSD",
        side="buy",
        entry_price=Decimal("1.08"),
        stop_loss_price=Decimal("1.07"),
    )

    bus.publish(intent)

    assert received == [intent]
