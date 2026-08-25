"""Predeclared directional-bias eligibility for separate ORB experiments."""

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum

from quantforge.backtest.models import MinuteBar
from quantforge.backtest.orb import NEW_YORK, to_new_york


class DirectionalBiasMode(StrEnum):
    """Directional filters whose definitions are versioned in configuration."""

    OVERNIGHT_OPEN_TO_PRE_RANGE_CLOSE = "overnight_open_to_pre_range_close"


@dataclass(frozen=True, slots=True)
class DirectionalBiasSettings:
    """The two pre-range M1 observations used by the selected bias rule."""

    mode: DirectionalBiasMode
    start_time: time
    end_time: time

    def __post_init__(self) -> None:
        if self.start_time >= self.end_time:
            raise ValueError("directional-bias start time must precede end time")


@dataclass(frozen=True, slots=True)
class EntryEligibility:
    """The only entry sides that a separate ORB experiment may activate."""

    sides: frozenset[str]
    reason: str

    def __post_init__(self) -> None:
        if not self.sides.issubset({"buy", "sell"}):
            raise ValueError("entry eligibility supports only buy and sell sides")
        if not self.reason:
            raise ValueError("entry eligibility requires an audit reason")


def determine_entry_eligibility(
    bars: tuple[MinuteBar, ...],
    *,
    session_day: date,
    settings: DirectionalBiasSettings | None,
) -> EntryEligibility:
    """Determine allowed entry side without consuming opening-range data."""
    if settings is None:
        return EntryEligibility(frozenset({"buy", "sell"}), "two-sided baseline entry")
    if settings.mode is not DirectionalBiasMode.OVERNIGHT_OPEN_TO_PRE_RANGE_CLOSE:
        raise ValueError(f"unsupported directional-bias mode: {settings.mode}")

    start = datetime.combine(session_day, settings.start_time, tzinfo=NEW_YORK)
    end = datetime.combine(session_day, settings.end_time, tzinfo=NEW_YORK)
    start_bars = tuple(bar for bar in bars if to_new_york(bar.timestamp) == start)
    end_bars = tuple(bar for bar in bars if to_new_york(bar.timestamp) == end)
    if len(start_bars) != 1 or len(end_bars) != 1:
        return EntryEligibility(
            frozenset(),
            (
                "directional bias unavailable: required pre-range M1 bar is "
                "missing or duplicate"
            ),
        )

    start_open = start_bars[0].open
    end_close = end_bars[0].close
    if start_open <= 0 or end_close <= 0:
        return EntryEligibility(
            frozenset(),
            "directional bias unavailable: required pre-range M1 price is invalid",
        )
    if end_close > start_open:
        return EntryEligibility(
            frozenset({"buy"}),
            "overnight bias is long: pre-range close is above overnight open",
        )
    if end_close < start_open:
        return EntryEligibility(
            frozenset({"sell"}),
            "overnight bias is short: pre-range close is below overnight open",
        )
    return EntryEligibility(
        frozenset(),
        "directional bias is neutral: pre-range close equals overnight open",
    )
