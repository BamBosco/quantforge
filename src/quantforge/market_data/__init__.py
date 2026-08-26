"""Market-data ports, validation, and normalization boundary."""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quantforge.backtest.models import MinuteBar
    from quantforge.market_data.mt5_bar_evidence import MT5BarEvidence


def load_mt5_minute_bars(
    path: Path, *, source_timezone: str
) -> tuple["MinuteBar", ...]:
    """Load MT5 bars lazily to keep the risk-policy import boundary acyclic."""
    from quantforge.market_data.mt5_csv import load_mt5_minute_bars as load

    return load(path, source_timezone=source_timezone)


def inspect_mt5_bar_evidence(path: Path) -> "MT5BarEvidence":
    """Inspect an MT5 export without guessing its source timezone."""
    from quantforge.market_data.mt5_bar_evidence import (
        inspect_mt5_bar_evidence as inspect,
    )

    return inspect(path)


__all__ = ["inspect_mt5_bar_evidence", "load_mt5_minute_bars"]
