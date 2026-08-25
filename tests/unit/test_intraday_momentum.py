"""Unit tests for the fixed, non-sized Intraday Momentum Experiment 001."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from quantforge.backtest.intraday_momentum import (
    IntradayMomentumSettings,
    simulate_intraday_momentum_session,
)
from quantforge.backtest.models import MinuteBar
from quantforge.backtest.replay import SessionOutcome, SimulationEventKind

SESSION_DAY = date(2026, 8, 14)


def settings() -> IntradayMomentumSettings:
    return IntradayMomentumSettings(
        timezone="America/New_York",
        signal_start=time(8, 20),
        entry_time=time(8, 50),
        exit_time=time(13, 30),
        signal_window_minutes=30,
        point_size=Decimal("0.01"),
        additional_slippage_points=Decimal("0"),
    )


def session_bars() -> list[MinuteBar]:
    start = datetime.combine(SESSION_DAY, time(8, 20), tzinfo=settings_timezone())
    return [
        MinuteBar(
            timestamp=start + timedelta(minutes=offset),
            open=Decimal("100"),
            high=Decimal("100"),
            low=Decimal("100"),
            close=Decimal("100"),
            tick_volume=1,
            spread_points=0,
        )
        for offset in range(311)
    ]


def settings_timezone():
    from zoneinfo import ZoneInfo

    return ZoneInfo("America/New_York")


def replace_bar(bars: list[MinuteBar], offset: int, **changes: Decimal) -> None:
    original = bars[offset]
    bars[offset] = MinuteBar(
        timestamp=original.timestamp,
        open=changes.get("open", original.open),
        high=changes.get("high", original.high),
        low=changes.get("low", original.low),
        close=changes.get("close", original.close),
        tick_volume=original.tick_volume,
        spread_points=original.spread_points,
    )


def test_bullish_signal_fills_then_forces_exit() -> None:
    bars = session_bars()
    replace_bar(bars, 0, low=Decimal("99"))
    replace_bar(bars, 29, high=Decimal("102"), close=Decimal("102"))
    replace_bar(
        bars,
        30,
        open=Decimal("103"),
        high=Decimal("103"),
        low=Decimal("102"),
        close=Decimal("103"),
    )
    replace_bar(
        bars,
        310,
        open=Decimal("105"),
        high=Decimal("105"),
        low=Decimal("105"),
        close=Decimal("105"),
    )

    result = simulate_intraday_momentum_session(
        bars, session_day=SESSION_DAY, settings=settings()
    )

    assert result.outcome is SessionOutcome.FORCED_EXIT
    assert result.entry_side == "buy"
    assert result.entry_price == Decimal("103")
    assert result.exit_price == Decimal("105")
    assert result.r_multiple == Decimal("0.5")
    assert [event.kind for event in result.events] == [
        SimulationEventKind.SIGNAL_COMPLETED,
        SimulationEventKind.RISK_APPROVED,
        SimulationEventKind.ENTRY_FILLED,
        SimulationEventKind.FORCED_EXIT,
    ]


def test_bearish_signal_uses_ask_based_stop_and_stops_out() -> None:
    bars = session_bars()
    replace_bar(bars, 0, high=Decimal("101"))
    replace_bar(bars, 29, low=Decimal("98"), close=Decimal("98"))
    replace_bar(
        bars,
        30,
        open=Decimal("98"),
        high=Decimal("99"),
        low=Decimal("98"),
        close=Decimal("98"),
    )
    replace_bar(
        bars,
        31,
        open=Decimal("101"),
        high=Decimal("102"),
        low=Decimal("101"),
        close=Decimal("101"),
    )

    result = simulate_intraday_momentum_session(
        bars, session_day=SESSION_DAY, settings=settings()
    )

    assert result.outcome is SessionOutcome.STOPPED_OUT
    assert result.entry_side == "sell"
    assert result.exit_price == Decimal("102")
    assert result.r_multiple == Decimal("-4") / Decimal("3")


def test_neutral_signal_is_explicitly_recorded_as_no_trade() -> None:
    result = simulate_intraday_momentum_session(
        session_bars(), session_day=SESSION_DAY, settings=settings()
    )

    assert result.outcome is SessionOutcome.NO_TRADE
    assert [event.kind for event in result.events] == [
        SimulationEventKind.SIGNAL_COMPLETED,
    ]


def test_entry_minute_stop_touch_is_ambiguous() -> None:
    bars = session_bars()
    replace_bar(bars, 0, low=Decimal("99"))
    replace_bar(bars, 29, high=Decimal("102"), close=Decimal("102"))
    replace_bar(
        bars,
        30,
        open=Decimal("103"),
        high=Decimal("103"),
        low=Decimal("98"),
        close=Decimal("100"),
    )

    result = simulate_intraday_momentum_session(
        bars, session_day=SESSION_DAY, settings=settings()
    )

    assert result.outcome is SessionOutcome.AMBIGUOUS
    assert result.events[-1].kind is SimulationEventKind.AMBIGUOUS


def test_missing_required_minute_is_invalid_data() -> None:
    bars = session_bars()
    del bars[60]

    result = simulate_intraday_momentum_session(
        bars, session_day=SESSION_DAY, settings=settings()
    )

    assert result.outcome is SessionOutcome.INVALID_DATA
    assert result.events[-1].kind is SimulationEventKind.INVALID_DATA
