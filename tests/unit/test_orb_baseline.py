from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from quantforge.backtest.models import MinuteBar, OpeningRange
from quantforge.backtest.orb import (
    OPENING_TIME,
    NEW_YORK,
    build_opening_range,
    calculate_stretch,
    entry_levels,
    protective_stop,
)


def make_bar(offset: int, high: str, low: str) -> MinuteBar:
    start = datetime(2026, 8, 14, OPENING_TIME.hour, OPENING_TIME.minute, tzinfo=NEW_YORK)
    return MinuteBar(
        timestamp=start.astimezone(ZoneInfo("UTC")) + timedelta(minutes=offset),
        open=Decimal("100"), high=Decimal(high), low=Decimal(low), close=Decimal("100"),
    )


def test_builds_complete_opening_range() -> None:
    bars = [make_bar(offset, "102", "99") for offset in range(15)]

    result = build_opening_range(bars, datetime(2026, 8, 14).date())

    assert result.high == Decimal("102")
    assert result.low == Decimal("99")


def test_rejects_missing_opening_range_data() -> None:
    bars = [make_bar(offset, "102", "99") for offset in range(14)]

    with pytest.raises(ValueError, match="missing or duplicate"):
        build_opening_range(bars, datetime(2026, 8, 14).date())


def test_calculates_ten_session_stretch_and_protective_stops() -> None:
    prior = [OpeningRange(Decimal("102"), Decimal("99"), Decimal("100")) for _ in range(10)]
    opening_range = OpeningRange(Decimal("110"), Decimal("100"), Decimal("105"))

    stretch = calculate_stretch(prior)
    long_entry, short_entry = entry_levels(opening_range, stretch)

    assert stretch == Decimal("1")
    assert (long_entry, short_entry) == (Decimal("111"), Decimal("99"))
    assert protective_stop("buy", opening_range, stretch) == Decimal("99")
    assert protective_stop("sell", opening_range, stretch) == Decimal("111")
