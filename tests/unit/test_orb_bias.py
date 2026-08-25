from datetime import date, datetime, time
from decimal import Decimal

from quantforge.backtest.models import MinuteBar
from quantforge.backtest.orb import NEW_YORK
from quantforge.backtest.orb_bias import (
    DirectionalBiasMode,
    DirectionalBiasSettings,
    determine_entry_eligibility,
)


DAY = date(2026, 8, 14)
SETTINGS = DirectionalBiasSettings(
    mode=DirectionalBiasMode.OVERNIGHT_OPEN_TO_PRE_RANGE_CLOSE,
    start_time=time(0),
    end_time=time(8, 19),
)


def bar(hour: int, minute: int, open_price: str, close_price: str) -> MinuteBar:
    return MinuteBar(
        timestamp=datetime(DAY.year, DAY.month, DAY.day, hour, minute, tzinfo=NEW_YORK),
        open=Decimal(open_price),
        high=max(Decimal(open_price), Decimal(close_price)),
        low=min(Decimal(open_price), Decimal(close_price)),
        close=Decimal(close_price),
        tick_volume=1,
        spread_points=0,
    )


def test_overnight_bias_allows_only_buy_after_upward_move() -> None:
    eligibility = determine_entry_eligibility(
        (bar(0, 0, "100", "100"), bar(8, 19, "101", "102")),
        session_day=DAY,
        settings=SETTINGS,
    )

    assert eligibility.sides == frozenset({"buy"})


def test_overnight_bias_allows_only_sell_after_downward_move() -> None:
    eligibility = determine_entry_eligibility(
        (bar(0, 0, "100", "100"), bar(8, 19, "99", "98")),
        session_day=DAY,
        settings=SETTINGS,
    )

    assert eligibility.sides == frozenset({"sell"})


def test_overnight_bias_returns_no_trade_when_required_bar_is_missing() -> None:
    eligibility = determine_entry_eligibility(
        (bar(0, 0, "100", "100"),),
        session_day=DAY,
        settings=SETTINGS,
    )

    assert eligibility.sides == frozenset()
    assert "missing" in eligibility.reason
