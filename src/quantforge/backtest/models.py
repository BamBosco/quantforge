"""Framework-independent records used by deterministic backtests."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MinuteBar:
    """One validated, UTC-timestamped minute of market data."""

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    tick_volume: int | None = None
    spread_points: int | None = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("market-data timestamps must be timezone-aware")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must not exceed open, close, or high")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must not be below open, close, or low")
        if self.tick_volume is not None and self.tick_volume < 0:
            raise ValueError("tick volume must not be negative")
        if self.spread_points is not None and self.spread_points < 0:
            raise ValueError("spread points must not be negative")


@dataclass(frozen=True, slots=True)
class OpeningRange:
    """The price range built during one configured opening window."""

    high: Decimal
    low: Decimal
    session_open: Decimal

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError("opening-range high must not be below low")
