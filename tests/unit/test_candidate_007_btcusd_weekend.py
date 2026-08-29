"""Unit tests verifying Candidate 007 24/7 weekend trading on BTCUSD."""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from quantforge.application.trading_pipeline import MarketFact
from quantforge.backtest.models import MinuteBar
from quantforge.strategies.candidate_007 import (
    Candidate007Settings,
    Candidate007Strategy,
)

NEW_YORK = ZoneInfo("America/New_York")


def make_bar(
    timestamp: datetime,
    price: Decimal,
    high_diff: Decimal = Decimal("100"),
    low_diff: Decimal = Decimal("100"),
) -> MinuteBar:
    return MinuteBar(
        timestamp=timestamp,
        open=price,
        high=price + high_diff,
        low=price - low_diff,
        close=price,
        tick_volume=100,
        spread_points=50,
    )


def test_candidate_007_btcusd_trades_on_saturday() -> None:
    # Saturday, Aug 29, 2026 at 11:30 AM NY
    saturday_ny = datetime(2026, 8, 29, 11, 30, tzinfo=NEW_YORK)
    assert saturday_ny.weekday() == 5  # 5 = Saturday

    strategy = Candidate007Strategy(settings=Candidate007Settings.for_btcusd())

    # Feed 70 upward trending warmup bars on Saturday morning
    start_time = saturday_ny - timedelta(minutes=70)
    for i in range(70):
        bar_time = start_time + timedelta(minutes=i)
        price = Decimal("65000.00") + (Decimal(str(i)) * Decimal("10.0"))
        strategy.update_bar(make_bar(bar_time, price))

    # Evaluate breakout market tick on Saturday
    market = MarketFact(
        instrument="BTCUSD",
        bid=Decimal("65800.00"),
        ask=Decimal("65805.00"),
        observed_at=saturday_ny,
        value_per_price_unit_per_lot=Decimal("1"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100.0"),
        volume_step=Decimal("0.01"),
    )

    signal = strategy.evaluate(market, evaluated_at=saturday_ny)

    assert signal is not None
    assert signal.instrument == "BTCUSD"
    assert signal.side == "buy"
    assert signal.entry_price == Decimal("65805.00")
    assert signal.stop_loss_price < signal.entry_price
    assert signal.target_price > signal.entry_price
