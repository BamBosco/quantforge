"""Conservative M1 replay for approved Intraday Momentum Experiment 001."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from quantforge.backtest.models import MinuteBar
from quantforge.backtest.replay import (
    ReplaySessionResult,
    SessionOutcome,
    SimulationEvent,
    SimulationEventKind,
    adverse_market_entry_price,
    adverse_market_exit_price,
    adverse_protective_stop_exit_price,
    ask_high,
    complete_minute_window,
    protective_stop_touched,
)
from quantforge.risk.validation import validate_protective_stop


@dataclass(frozen=True, slots=True)
class IntradayMomentumSettings:
    """Configuration-derived inputs for the fixed momentum replay."""

    timezone: str
    signal_start: time
    entry_time: time
    exit_time: time
    signal_window_minutes: int
    point_size: Decimal
    additional_slippage_points: Decimal

    def __post_init__(self) -> None:
        if not self.timezone:
            raise ValueError("strategy timezone must not be empty")
        if not self.signal_start < self.entry_time < self.exit_time:
            raise ValueError("momentum session times must be strictly ordered")
        if self.signal_window_minutes <= 0:
            raise ValueError("momentum signal window must be positive")
        observed_window_minutes = (
            self.entry_time.hour * 60
            + self.entry_time.minute
            - self.signal_start.hour * 60
            - self.signal_start.minute
        )
        if observed_window_minutes != self.signal_window_minutes:
            raise ValueError("entry time must follow the configured signal window")
        if self.point_size <= 0:
            raise ValueError("point size must be positive")
        if self.additional_slippage_points < 0:
            raise ValueError("additional slippage points must not be negative")

    @property
    def additional_slippage(self) -> Decimal:
        """Configured adverse slippage represented as price."""
        return self.point_size * self.additional_slippage_points


@dataclass(frozen=True, slots=True)
class _Position:
    side: str
    entry_price: Decimal
    stop: Decimal


def simulate_intraday_momentum_session(
    bars: Iterable[MinuteBar],
    *,
    session_day: date,
    settings: IntradayMomentumSettings,
) -> ReplaySessionResult:
    """Replay one price-only session without inventing intrabar fill order."""
    timezone = ZoneInfo(settings.timezone)
    signal_start = datetime.combine(session_day, settings.signal_start, tzinfo=timezone)
    entry_at = datetime.combine(session_day, settings.entry_time, tzinfo=timezone)
    exit_at = datetime.combine(session_day, settings.exit_time, tzinfo=timezone)
    session_bars = complete_minute_window(bars, start=signal_start, end=exit_at)
    if session_bars is None:
        return _terminal(
            session_day,
            signal_start,
            SessionOutcome.INVALID_DATA,
            SimulationEventKind.INVALID_DATA,
            "missing, duplicate, or spreadless M1 data in the required session window",
        )

    by_time = {bar.timestamp.astimezone(timezone): bar for bar in session_bars}
    signal_bars = tuple(
        by_time[signal_start + timedelta(minutes=offset)]
        for offset in range(settings.signal_window_minutes)
    )
    signal_open = signal_bars[0].open
    signal_close = signal_bars[-1].close
    events = [
        SimulationEvent(
            timestamp=entry_at,
            kind=SimulationEventKind.SIGNAL_COMPLETED,
            detail=(
                f"{settings.signal_window_minutes}-minute price-momentum "
                "signal completed"
            ),
        )
    ]
    if signal_close == signal_open:
        return ReplaySessionResult(session_day, SessionOutcome.NO_TRADE, tuple(events))
    side = "buy" if signal_close > signal_open else "sell"
    entry_bar = by_time[entry_at]
    entry_price = adverse_market_entry_price(
        side,
        entry_bar,
        point_size=settings.point_size,
        additional_slippage=settings.additional_slippage,
    )
    stop = _protective_stop(side, signal_bars, settings.point_size)
    risk = validate_protective_stop(side, entry_price, stop)
    if not risk.approved:
        events.append(
            SimulationEvent(
                entry_at,
                SimulationEventKind.RISK_REJECTED,
                "; ".join(risk.reasons),
            )
        )
        return ReplaySessionResult(session_day, SessionOutcome.REJECTED, tuple(events))
    events.append(
        SimulationEvent(
            entry_at,
            SimulationEventKind.RISK_APPROVED,
            "protective-stop shape approved for non-sized research intent",
        )
    )
    if protective_stop_touched(side, entry_bar, stop, point_size=settings.point_size):
        events.append(
            SimulationEvent(
                entry_at,
                SimulationEventKind.AMBIGUOUS,
                "entry minute also touched the protective stop; tick order is unknown",
            )
        )
        return ReplaySessionResult(session_day, SessionOutcome.AMBIGUOUS, tuple(events))

    position = _Position(side, entry_price, stop)
    events.append(
        SimulationEvent(
            entry_at,
            SimulationEventKind.ENTRY_FILLED,
            f"{side} market entry filled",
            entry_price,
        )
    )
    for bar in session_bars:
        timestamp = bar.timestamp.astimezone(timezone)
        if timestamp <= entry_at:
            continue
        if timestamp == exit_at:
            exit_price = adverse_market_exit_price(
                position.side,
                bar,
                point_size=settings.point_size,
                additional_slippage=settings.additional_slippage,
            )
            events.append(
                SimulationEvent(
                    timestamp,
                    SimulationEventKind.FORCED_EXIT,
                    "position closed at configured session exit",
                    exit_price,
                )
            )
            return _closed(
                session_day,
                SessionOutcome.FORCED_EXIT,
                tuple(events),
                position,
                exit_price,
            )
        if protective_stop_touched(
            position.side, bar, position.stop, point_size=settings.point_size
        ):
            exit_price = adverse_protective_stop_exit_price(
                position.side,
                bar,
                position.stop,
                point_size=settings.point_size,
                additional_slippage=settings.additional_slippage,
            )
            events.append(
                SimulationEvent(
                    timestamp,
                    SimulationEventKind.STOP_FILLED,
                    "protective stop filled with adverse gap/slippage handling",
                    exit_price,
                )
            )
            return _closed(
                session_day,
                SessionOutcome.STOPPED_OUT,
                tuple(events),
                position,
                exit_price,
            )
    return _terminal(
        session_day,
        exit_at,
        SessionOutcome.INVALID_DATA,
        SimulationEventKind.INVALID_DATA,
        "required forced-exit M1 bar was not reached",
    )


def _protective_stop(
    side: str, signal_bars: tuple[MinuteBar, ...], point_size: Decimal
) -> Decimal:
    if side == "buy":
        return min(bar.low for bar in signal_bars)
    return max(ask_high(bar, point_size) for bar in signal_bars)


def _closed(
    session_day: date,
    outcome: SessionOutcome,
    events: tuple[SimulationEvent, ...],
    position: _Position,
    exit_price: Decimal,
) -> ReplaySessionResult:
    risk_per_unit = abs(position.entry_price - position.stop)
    if risk_per_unit <= 0:
        raise ValueError("simulated position has non-positive risk")
    gross_pnl = (
        exit_price - position.entry_price
        if position.side == "buy"
        else position.entry_price - exit_price
    )
    return ReplaySessionResult(
        session_day=session_day,
        outcome=outcome,
        events=events,
        entry_side=position.side,
        entry_price=position.entry_price,
        exit_price=exit_price,
        r_multiple=gross_pnl / risk_per_unit,
    )


def _terminal(
    session_day: date,
    timestamp: datetime,
    outcome: SessionOutcome,
    kind: SimulationEventKind,
    detail: str,
) -> ReplaySessionResult:
    return ReplaySessionResult(
        session_day, outcome, (SimulationEvent(timestamp, kind, detail),)
    )
