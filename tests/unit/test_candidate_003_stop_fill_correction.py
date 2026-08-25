from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from quantforge.backtest.candidate_003 import simulate_session
from quantforge.backtest.models import MinuteBar
from quantforge.backtest.replay import adverse_protective_stop_exit_price

POINT = Decimal("0.001")


def _bar(
    moment: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
    spread: int = 2,
) -> MinuteBar:
    return MinuteBar(
        moment,
        Decimal(open_),
        Decimal(high),
        Decimal(low),
        Decimal(close),
        1,
        spread,
    )


def _session(day: date, *, first_open: str, last_close: str) -> list[MinuteBar]:
    start = datetime(day.year, day.month, day.day, 13, 20, tzinfo=UTC)
    bars = [
        _bar(
            start + timedelta(minutes=index),
            open_="100",
            high="102",
            low="99",
            close="100",
        )
        for index in range(311)
    ]
    bars[0] = _bar(start, open_=first_open, high="102", low="99", close="100")
    bars[4] = _bar(
        start + timedelta(minutes=4),
        open_="100",
        high="102",
        low="99",
        close=last_close,
    )
    bars[5] = _bar(
        start + timedelta(minutes=5),
        open_="100",
        high="102",
        low="99.5",
        close="100",
    )
    return bars


def test_long_stop_uses_bid_low_for_intrabar_and_gap_fills() -> None:
    moment = datetime(2024, 1, 2, 13, 26, tzinfo=UTC)
    intrabar = _bar(moment, open_="100", high="101", low="97", close="98")
    gap = _bar(moment, open_="98", high="99", low="97", close="97.5")
    for points in (Decimal("0"), Decimal("1"), Decimal("3")):
        slippage = POINT * points
        assert (
            adverse_protective_stop_exit_price(
                "buy",
                intrabar,
                Decimal("99"),
                point_size=POINT,
                additional_slippage=slippage,
            )
            == Decimal("97") - slippage
        )
        assert (
            adverse_protective_stop_exit_price(
                "buy",
                gap,
                Decimal("99"),
                point_size=POINT,
                additional_slippage=slippage,
            )
            == Decimal("97") - slippage
        )


def test_short_stop_uses_ask_high_for_intrabar_and_gap_fills() -> None:
    moment = datetime(2024, 1, 2, 13, 26, tzinfo=UTC)
    intrabar = _bar(moment, open_="100", high="104", low="99", close="103")
    gap = _bar(moment, open_="102", high="104", low="101", close="103")
    for points in (Decimal("0"), Decimal("1"), Decimal("3")):
        slippage = POINT * points
        expected = Decimal("104.002") + slippage
        assert (
            adverse_protective_stop_exit_price(
                "sell",
                intrabar,
                Decimal("101"),
                point_size=POINT,
                additional_slippage=slippage,
            )
            == expected
        )
        assert (
            adverse_protective_stop_exit_price(
                "sell",
                gap,
                Decimal("101"),
                point_size=POINT,
                additional_slippage=slippage,
            )
            == expected
        )


def test_corrected_stop_fill_propagates_to_long_and_short_r() -> None:
    day = date(2024, 1, 2)
    long_bars = _session(day, first_open="100", last_close="101")
    long_bars[6] = _bar(
        long_bars[6].timestamp,
        open_="100",
        high="101",
        low="98",
        close="99",
    )
    long = simulate_session(long_bars, session_day=day, slippage_points=Decimal("0"))
    assert long.exit_price == Decimal("98")
    assert long.r_multiple == Decimal("-2.002") / Decimal("1.002")

    short_bars = _session(day, first_open="100", last_close="99")
    short_bars[5] = _bar(
        short_bars[5].timestamp,
        open_="100",
        high="101",
        low="99.5",
        close="100",
    )
    short_bars[6] = _bar(
        short_bars[6].timestamp,
        open_="100",
        high="104",
        low="99",
        close="103",
    )
    short = simulate_session(short_bars, session_day=day, slippage_points=Decimal("0"))
    assert short.exit_price == Decimal("104.002")
    assert short.r_multiple == Decimal("-4.002") / Decimal("2.002")
