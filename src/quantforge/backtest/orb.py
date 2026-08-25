"""Pure calculations for the approved ORB research baseline."""

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from quantforge.backtest.models import MinuteBar, OpeningRange

NEW_YORK = ZoneInfo("America/New_York")
OPENING_TIME = time(8, 20)
OPENING_RANGE_MINUTES = 15


def to_new_york(timestamp: datetime) -> datetime:
    """Convert an aware timestamp to the strategy's configured timezone."""
    if timestamp.tzinfo is None:
        raise ValueError("market-data timestamps must be timezone-aware")
    return timestamp.astimezone(NEW_YORK)


def build_opening_range(bars: Iterable[MinuteBar], session_day: date) -> OpeningRange:
    """Build an 08:20-08:35 New York range only from complete minute data."""
    window_start = datetime.combine(session_day, OPENING_TIME, tzinfo=NEW_YORK)
    expected = {
        window_start + timedelta(minutes=offset)
        for offset in range(OPENING_RANGE_MINUTES)
    }
    selected = [bar for bar in bars if to_new_york(bar.timestamp) in expected]
    seen = {to_new_york(bar.timestamp) for bar in selected}
    if seen != expected or len(selected) != len(expected):
        raise ValueError("opening range has missing or duplicate minute bars")
    return OpeningRange(
        high=max(bar.high for bar in selected),
        low=min(bar.low for bar in selected),
        session_open=selected[0].open,
    )


def calculate_stretch(prior_ranges: Iterable[OpeningRange]) -> Decimal:
    """Calculate Crabel-style Stretch from exactly ten completed sessions."""
    ranges = list(prior_ranges)
    if len(ranges) != 10:
        raise ValueError("Stretch requires exactly ten completed sessions")
    distances = [
        min(
            abs(item.high - item.session_open),
            abs(item.session_open - item.low),
        )
        for item in ranges
    ]
    return sum(distances, start=Decimal("0")) / Decimal(len(distances))


def entry_levels(
    opening_range: OpeningRange,
    stretch: Decimal,
) -> tuple[Decimal, Decimal]:
    """Return the approved long and short breakout-stop trigger levels."""
    if stretch <= 0:
        raise ValueError("Stretch must be positive")
    return opening_range.high + stretch, opening_range.low - stretch


def protective_stop(
    side: str,
    opening_range: OpeningRange,
    stretch: Decimal,
) -> Decimal:
    """Return the opposite-range protective stop required by the baseline."""
    long_entry, short_entry = entry_levels(opening_range, stretch)
    if side == "buy":
        return short_entry
    if side == "sell":
        return long_entry
    raise ValueError("side must be 'buy' or 'sell'")
