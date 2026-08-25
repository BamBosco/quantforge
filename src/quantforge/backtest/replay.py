"""Strategy-neutral records and M1 continuity checks for offline replays."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from quantforge.backtest.models import MinuteBar
from quantforge.backtest.validation import ValidationSession


class SessionOutcome(StrEnum):
    """Terminal states permitted for one non-sized replay session."""

    NO_TRADE = "no_trade"
    STOPPED_OUT = "stopped_out"
    FORCED_EXIT = "forced_exit"
    AMBIGUOUS = "ambiguous"
    REJECTED = "rejected"
    INVALID_DATA = "invalid_data"


class SimulationEventKind(StrEnum):
    """Auditable events emitted by deterministic research replays."""

    RANGE_COMPLETED = "range_completed"
    SIGNAL_COMPLETED = "signal_completed"
    RISK_APPROVED = "risk_approved"
    RISK_REJECTED = "risk_rejected"
    ENTRY_FILLED = "entry_filled"
    OCO_CANCELED = "oco_canceled"
    DIRECTIONAL_BIAS_NO_TRADE = "directional_bias_no_trade"
    STOP_FILLED = "stop_filled"
    FORCED_EXIT = "forced_exit"
    AMBIGUOUS = "ambiguous"
    INVALID_DATA = "invalid_data"


@dataclass(frozen=True, slots=True)
class SimulationEvent:
    """An immutable journal event from one offline research replay."""

    timestamp: datetime
    kind: SimulationEventKind
    detail: str
    price: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ReplaySessionResult:
    """Complete non-sized terminal outcome for one replay session."""

    session_day: date
    outcome: SessionOutcome
    events: tuple[SimulationEvent, ...]
    entry_side: str | None = None
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    r_multiple: Decimal | None = None


@dataclass(frozen=True, slots=True)
class SkippedSession:
    """A session excluded before replay with the permanent reason recorded."""

    session_day: date
    reason: str


def to_validation_sessions(
    results: Iterable[ReplaySessionResult],
) -> tuple[ValidationSession, ...]:
    """Adapt non-sized replay outcomes to the strategy-neutral validation API."""
    return tuple(
        ValidationSession(result.session_day, result.r_multiple) for result in results
    )


def complete_minute_window(
    bars: Iterable[MinuteBar],
    *,
    start: datetime,
    end: datetime,
) -> tuple[MinuteBar, ...] | None:
    """Return an exact M1 window, otherwise reject it as unusable research data.

    The bounds are inclusive because an exit at a bar open requires that bar's
    opening quote. Duplicate timestamps, missing minutes, and missing recorded
    spreads all invalidate the window.
    """
    if start.tzinfo is None or end.tzinfo is None or end < start:
        raise ValueError("replay window requires ordered timezone-aware bounds")
    expected = {
        start + timedelta(minutes=offset)
        for offset in range(_minutes_between(start, end) + 1)
    }
    selected = tuple(
        bar for bar in bars if start <= bar.timestamp.astimezone(start.tzinfo) <= end
    )
    observed = [bar.timestamp.astimezone(start.tzinfo) for bar in selected]
    if len(selected) != len(expected) or set(observed) != expected:
        return None
    if any(bar.spread_points is None for bar in selected):
        return None
    return tuple(sorted(selected, key=lambda bar: bar.timestamp))


def terminal_result(
    *,
    session_day: date,
    timestamp: datetime,
    outcome: SessionOutcome,
    event_kind: SimulationEventKind,
    detail: str,
) -> ReplaySessionResult:
    """Create an explicit non-trade terminal state for auditability."""
    return ReplaySessionResult(
        session_day=session_day,
        outcome=outcome,
        events=(SimulationEvent(timestamp, event_kind, detail),),
    )


def adverse_market_entry_price(
    side: str,
    bar: MinuteBar,
    *,
    point_size: Decimal,
    additional_slippage: Decimal,
) -> Decimal:
    """Price a market entry at the bar open using bid/ask and adverse slippage."""
    if side == "buy":
        return ask_open(bar, point_size) + additional_slippage
    if side == "sell":
        return bar.open - additional_slippage
    raise ValueError("side must be buy or sell")


def adverse_market_exit_price(
    side: str,
    bar: MinuteBar,
    *,
    point_size: Decimal,
    additional_slippage: Decimal,
) -> Decimal:
    """Price a market exit at the bar open on the adverse executable side."""
    if side == "buy":
        return bar.open - additional_slippage
    if side == "sell":
        return ask_open(bar, point_size) + additional_slippage
    raise ValueError("side must be buy or sell")


def protective_stop_touched(
    side: str,
    bar: MinuteBar,
    stop: Decimal,
    *,
    point_size: Decimal,
) -> bool:
    """Check stop touch using bid for longs and ask for shorts."""
    if side == "buy":
        return bar.low <= stop
    if side == "sell":
        return ask_high(bar, point_size) >= stop
    raise ValueError("side must be buy or sell")


def adverse_protective_stop_exit_price(
    side: str,
    bar: MinuteBar,
    stop: Decimal,
    *,
    point_size: Decimal,
    additional_slippage: Decimal,
) -> Decimal:
    """Apply a conservative gap/slippage assumption to a protective stop."""
    if side == "buy":
        return min(bar.low, stop) - additional_slippage
    if side == "sell":
        return max(ask_high(bar, point_size), stop) + additional_slippage
    raise ValueError("side must be buy or sell")


def ask_open(bar: MinuteBar, point_size: Decimal) -> Decimal:
    """Convert a bid bar open to its recorded ask equivalent."""
    return bar.open + spread_as_price(bar, point_size)


def ask_high(bar: MinuteBar, point_size: Decimal) -> Decimal:
    """Convert a bid bar high to its recorded ask equivalent."""
    return bar.high + spread_as_price(bar, point_size)


def spread_as_price(bar: MinuteBar, point_size: Decimal) -> Decimal:
    """Return the recorded M1 spread as price, never a guessed spread."""
    if point_size <= 0:
        raise ValueError("point size must be positive")
    if bar.spread_points is None:
        raise ValueError("M1 bar has no spread")
    return Decimal(bar.spread_points) * point_size


def _minutes_between(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)
