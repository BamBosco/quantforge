"""Conservative M1 event replay for the approved, research-only ORB baseline."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum

from quantforge.backtest.models import MinuteBar, OpeningRange
from quantforge.backtest.orb import (
    NEW_YORK,
    OPENING_RANGE_MINUTES,
    OPENING_TIME,
    build_opening_range,
    calculate_stretch,
    entry_levels,
    protective_stop,
    to_new_york,
)
from quantforge.backtest.orb_bias import DirectionalBiasSettings, EntryEligibility
from quantforge.risk.validation import validate_protective_stop


class SessionOutcome(StrEnum):
    """Terminal states allowed for one simulated ORB session."""

    NO_TRADE = "no_trade"
    STOPPED_OUT = "stopped_out"
    FORCED_EXIT = "forced_exit"
    AMBIGUOUS = "ambiguous"
    REJECTED = "rejected"
    INVALID_DATA = "invalid_data"


class SimulationEventKind(StrEnum):
    """Journal entries produced by the deterministic simulation."""

    RANGE_COMPLETED = "range_completed"
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
class OrbSimulationSettings:
    """Instrument-specific assumptions supplied by approved configuration."""

    point_size: Decimal
    additional_slippage_points: Decimal
    exit_time: time = time(13, 30)
    directional_bias: DirectionalBiasSettings | None = None

    def __post_init__(self) -> None:
        if self.point_size <= 0:
            raise ValueError("point size must be positive")
        if self.additional_slippage_points < 0:
            raise ValueError("additional slippage points must not be negative")

    @property
    def additional_slippage(self) -> Decimal:
        """Convert the configured adverse slippage to a price increment."""
        return self.point_size * self.additional_slippage_points


@dataclass(frozen=True, slots=True)
class SimulationEvent:
    """An immutable, ordered research-journal event."""

    timestamp: datetime
    kind: SimulationEventKind
    detail: str
    price: Decimal | None = None


@dataclass(frozen=True, slots=True)
class OrbSessionResult:
    """The complete non-sized outcome of one ORB session simulation."""

    session_day: date
    outcome: SessionOutcome
    events: tuple[SimulationEvent, ...]
    entry_side: str | None = None
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    r_multiple: Decimal | None = None


def simulate_orb_session(
    bars: Iterable[MinuteBar],
    *,
    session_day: date,
    prior_ranges: Iterable[OpeningRange],
    settings: OrbSimulationSettings,
    entry_eligibility: EntryEligibility | None = None,
) -> OrbSessionResult:
    """Replay one session without fabricating fills from ambiguous M1 OHLC bars.

    Prices are taken from bid OHLC data. Buy entries and short exits are
    converted to ask using each bar's recorded spread. Every slippage adjustment
    is adverse. This does not simulate order quantity; risk sizing remains
    outside the strategy and is deliberately absent from this research replay.
    """
    session_bars = complete_session_bars(bars, session_day, settings.exit_time)
    if session_bars is None:
        return _terminal_result(
            session_day,
            SessionOutcome.INVALID_DATA,
            SimulationEventKind.INVALID_DATA,
            "missing, duplicate, or spreadless M1 data in the required session window",
        )

    try:
        opening_range = build_opening_range(session_bars, session_day)
        stretch = calculate_stretch(prior_ranges)
        long_entry, short_entry = entry_levels(opening_range, stretch)
    except ValueError as error:
        return _terminal_result(
            session_day,
            SessionOutcome.REJECTED,
            SimulationEventKind.RISK_REJECTED,
            str(error),
        )

    range_end = datetime.combine(
        session_day,
        OPENING_TIME,
        tzinfo=NEW_YORK,
    ) + timedelta(minutes=OPENING_RANGE_MINUTES)
    events = [
        SimulationEvent(
            timestamp=range_end,
            kind=SimulationEventKind.RANGE_COMPLETED,
            detail="opening range completed; OCO stop entries activated",
        ),
    ]
    eligibility = entry_eligibility or EntryEligibility(
        frozenset({"buy", "sell"}), "two-sided baseline entry"
    )
    if not eligibility.sides:
        events.append(
            SimulationEvent(
                timestamp=range_end,
                kind=SimulationEventKind.DIRECTIONAL_BIAS_NO_TRADE,
                detail=eligibility.reason,
            )
        )
        return OrbSessionResult(session_day, SessionOutcome.NO_TRADE, tuple(events))
    try:
        _validate_risk_shape(
            opening_range,
            stretch,
            long_entry,
            short_entry,
            eligibility.sides,
        )
    except ValueError as error:
        return _terminal_result(
            session_day,
            SessionOutcome.REJECTED,
            SimulationEventKind.RISK_REJECTED,
            str(error),
        )
    events.append(
        SimulationEvent(
            timestamp=range_end,
            kind=SimulationEventKind.RISK_APPROVED,
            detail="protective-stop shape approved for non-sized research intent",
        )
    )
    position: _Position | None = None
    exit_at = datetime.combine(session_day, settings.exit_time, tzinfo=NEW_YORK)

    for bar in session_bars:
        timestamp = to_new_york(bar.timestamp)
        if timestamp < range_end:
            continue
        if timestamp == exit_at:
            if position is None:
                return OrbSessionResult(
                    session_day,
                    SessionOutcome.NO_TRADE,
                    tuple(events),
                )
            exit_price = _forced_exit_price(position.side, bar, settings)
            events.append(
                SimulationEvent(
                    timestamp=timestamp,
                    kind=SimulationEventKind.FORCED_EXIT,
                    detail="position closed at the configured session exit",
                    price=exit_price,
                )
            )
            return _closed_result(
                session_day,
                SessionOutcome.FORCED_EXIT,
                tuple(events),
                position,
                exit_price,
            )

        if position is None:
            long_touched = "buy" in eligibility.sides and _buy_stop_touched(
                bar, long_entry, settings
            )
            short_touched = "sell" in eligibility.sides and _sell_stop_touched(
                bar, short_entry
            )
            if long_touched and short_touched:
                events.append(
                    SimulationEvent(
                        timestamp=timestamp,
                        kind=SimulationEventKind.AMBIGUOUS,
                        detail=(
                            "both OCO entries touched in one M1 bar; "
                            "tick order is unknown"
                        ),
                    )
                )
                return OrbSessionResult(
                    session_day,
                    SessionOutcome.AMBIGUOUS,
                    tuple(events),
                )
            if long_touched:
                entry_price = _buy_stop_fill_price(bar, long_entry, settings)
                if _protective_stop_touched("buy", bar, short_entry, settings):
                    return _ambiguous_entry_and_stop_result(
                        session_day,
                        events,
                        timestamp,
                        "buy",
                    )
                position = _Position("buy", entry_price, short_entry)
                events.extend(
                    _entry_events(
                        timestamp,
                        "buy",
                        entry_price,
                        has_opposing_entry="sell" in eligibility.sides,
                    )
                )
            elif short_touched:
                entry_price = _sell_stop_fill_price(bar, short_entry, settings)
                if _protective_stop_touched("sell", bar, long_entry, settings):
                    return _ambiguous_entry_and_stop_result(
                        session_day,
                        events,
                        timestamp,
                        "sell",
                    )
                position = _Position("sell", entry_price, long_entry)
                events.extend(
                    _entry_events(
                        timestamp,
                        "sell",
                        entry_price,
                        has_opposing_entry="buy" in eligibility.sides,
                    )
                )
            continue

        if _protective_stop_touched(position.side, bar, position.stop, settings):
            exit_price = _protective_stop_fill_price(
                position.side,
                bar,
                position.stop,
                settings,
            )
            events.append(
                SimulationEvent(
                    timestamp=timestamp,
                    kind=SimulationEventKind.STOP_FILLED,
                    detail="protective stop filled with adverse gap/slippage handling",
                    price=exit_price,
                )
            )
            return _closed_result(
                session_day,
                SessionOutcome.STOPPED_OUT,
                tuple(events),
                position,
                exit_price,
            )

    return _terminal_result(
        session_day,
        SessionOutcome.INVALID_DATA,
        SimulationEventKind.INVALID_DATA,
        "required forced-exit M1 bar was not reached",
    )


@dataclass(frozen=True, slots=True)
class _Position:
    side: str
    entry_price: Decimal
    stop: Decimal


def complete_session_bars(
    bars: Iterable[MinuteBar], session_day: date, exit_time: time
) -> tuple[MinuteBar, ...] | None:
    """Require an exact continuous M1 sequence through the forced-exit bar."""
    start = datetime.combine(session_day, OPENING_TIME, tzinfo=NEW_YORK)
    end = datetime.combine(session_day, exit_time, tzinfo=NEW_YORK)
    expected = {
        start + timedelta(minutes=offset)
        for offset in range(_minutes_between(start, end) + 1)
    }
    selected = tuple(bar for bar in bars if start <= to_new_york(bar.timestamp) <= end)
    observed = [to_new_york(bar.timestamp) for bar in selected]
    if len(selected) != len(expected) or set(observed) != expected:
        return None
    if any(bar.spread_points is None for bar in selected):
        return None
    return tuple(sorted(selected, key=lambda bar: bar.timestamp))


def _minutes_between(start: datetime, end: datetime) -> int:
    """Return the exact number of whole minutes in an aware session interval."""
    return int((end - start).total_seconds() // 60)


def _validate_risk_shape(
    opening_range: OpeningRange,
    stretch: Decimal,
    long_entry: Decimal,
    short_entry: Decimal,
    eligible_sides: frozenset[str],
) -> None:
    """Route each eligible non-sized intent through shared risk validation."""
    checks = []
    if "buy" in eligible_sides:
        checks.append(
            validate_protective_stop(
                "buy", long_entry, protective_stop("buy", opening_range, stretch)
            )
        )
    if "sell" in eligible_sides:
        checks.append(
            validate_protective_stop(
                "sell", short_entry, protective_stop("sell", opening_range, stretch)
            )
        )
    if not all(check.approved for check in checks):
        reasons = tuple(reason for check in checks for reason in check.reasons)
        raise ValueError("risk rejected ORB intent: " + "; ".join(reasons))


def _entry_events(
    timestamp: datetime,
    side: str,
    price: Decimal,
    *,
    has_opposing_entry: bool,
) -> tuple[SimulationEvent, ...]:
    """Journal a fill and, when present, atomic cancellation of its OCO peer."""
    peer = "sell" if side == "buy" else "buy"
    events = [
        SimulationEvent(
            timestamp,
            SimulationEventKind.ENTRY_FILLED,
            f"{side} stop filled",
            price,
        )
    ]
    if has_opposing_entry:
        events.append(
            SimulationEvent(
                timestamp,
                SimulationEventKind.OCO_CANCELED,
                f"opposing {peer} stop canceled atomically",
            )
        )
    return tuple(events)


def _buy_stop_touched(
    bar: MinuteBar, trigger: Decimal, settings: OrbSimulationSettings
) -> bool:
    return _ask_high(bar, settings) >= trigger


def _sell_stop_touched(bar: MinuteBar, trigger: Decimal) -> bool:
    return bar.low <= trigger


def _buy_stop_fill_price(
    bar: MinuteBar,
    trigger: Decimal,
    settings: OrbSimulationSettings,
) -> Decimal:
    return max(_ask_open(bar, settings), trigger) + settings.additional_slippage


def _sell_stop_fill_price(
    bar: MinuteBar,
    trigger: Decimal,
    settings: OrbSimulationSettings,
) -> Decimal:
    return min(bar.open, trigger) - settings.additional_slippage


def _protective_stop_touched(
    side: str, bar: MinuteBar, stop: Decimal, settings: OrbSimulationSettings
) -> bool:
    if side == "buy":
        return bar.low <= stop
    return _ask_high(bar, settings) >= stop


def _protective_stop_fill_price(
    side: str, bar: MinuteBar, stop: Decimal, settings: OrbSimulationSettings
) -> Decimal:
    if side == "buy":
        return min(bar.open, stop) - settings.additional_slippage
    return max(_ask_open(bar, settings), stop) + settings.additional_slippage


def _forced_exit_price(
    side: str,
    bar: MinuteBar,
    settings: OrbSimulationSettings,
) -> Decimal:
    if side == "buy":
        return bar.open - settings.additional_slippage
    return _ask_open(bar, settings) + settings.additional_slippage


def _ask_open(bar: MinuteBar, settings: OrbSimulationSettings) -> Decimal:
    return bar.open + _spread_as_price(bar, settings)


def _ask_high(bar: MinuteBar, settings: OrbSimulationSettings) -> Decimal:
    return bar.high + _spread_as_price(bar, settings)


def _spread_as_price(bar: MinuteBar, settings: OrbSimulationSettings) -> Decimal:
    """Use the recorded bar spread; coverage validation requires it to exist."""
    if bar.spread_points is None:
        raise ValueError("M1 bar has no spread")
    return Decimal(bar.spread_points) * settings.point_size


def _closed_result(
    session_day: date,
    outcome: SessionOutcome,
    events: tuple[SimulationEvent, ...],
    position: _Position,
    exit_price: Decimal,
) -> OrbSessionResult:
    risk_per_unit = abs(position.entry_price - position.stop)
    if risk_per_unit <= 0:
        raise ValueError("simulated position has non-positive risk")
    gross_pnl = (
        exit_price - position.entry_price
        if position.side == "buy"
        else position.entry_price - exit_price
    )
    return OrbSessionResult(
        session_day=session_day,
        outcome=outcome,
        events=events,
        entry_side=position.side,
        entry_price=position.entry_price,
        exit_price=exit_price,
        r_multiple=gross_pnl / risk_per_unit,
    )


def _terminal_result(
    session_day: date,
    outcome: SessionOutcome,
    event_kind: SimulationEventKind,
    detail: str,
) -> OrbSessionResult:
    """Return a non-trade terminal result with an explicit audit event."""
    timestamp = datetime.combine(session_day, OPENING_TIME, tzinfo=NEW_YORK)
    return OrbSessionResult(
        session_day=session_day,
        outcome=outcome,
        events=(SimulationEvent(timestamp, event_kind, detail),),
    )


def _ambiguous_entry_and_stop_result(
    session_day: date,
    events: list[SimulationEvent],
    timestamp: datetime,
    side: str,
) -> OrbSessionResult:
    """Reject an M1 bar that could contain both entry and protective-stop fills."""
    events.append(
        SimulationEvent(
            timestamp=timestamp,
            kind=SimulationEventKind.AMBIGUOUS,
            detail=(
                f"{side} entry and its protective stop touched in one M1 bar; "
                "tick order is unknown"
            ),
        )
    )
    return OrbSessionResult(session_day, SessionOutcome.AMBIGUOUS, tuple(events))
