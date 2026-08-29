"""Candidate 007 deterministic historical replay and simulation engine."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from quantforge.backtest.models import MinuteBar
from quantforge.backtest.replay import (
    ReplaySessionResult,
    SessionOutcome,
    SimulationEvent,
    SimulationEventKind,
)

NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class Candidate007SimulationSettings:
    """Settings for deterministic Candidate 007 session simulation."""

    atr_period: int = 14
    atr_ma_period: int = 50
    ema_trend_period: int = 50
    breakout_channel_bars: int = 20
    risk_reward_ratio: Decimal = Decimal("2.0")
    min_stop_distance: Decimal = Decimal("1.5")
    point_size: Decimal = Decimal("0.01")
    additional_slippage_points: Decimal = Decimal("0")
    session_start_ny: time = time(8, 30)
    session_end_ny: time = time(12, 30)
    exit_time_ny: time = time(13, 30)


def simulate_candidate_007_session(
    session_day: date,
    session_bars: Sequence[MinuteBar],
    warmup_bars: Sequence[MinuteBar],
    settings: Candidate007SimulationSettings,
) -> ReplaySessionResult:
    """Simulate one day's M1 bars for Candidate 007 with explicit spread and slippage."""
    events: list[SimulationEvent] = []

    if not session_bars:
        return ReplaySessionResult(
            session_day=session_day,
            outcome=SessionOutcome.INVALID_DATA,
            events=(
                SimulationEvent(
                    timestamp=datetime.combine(
                        session_day, time(0, 0), tzinfo=NEW_YORK
                    ).astimezone(UTC),
                    kind=SimulationEventKind.INVALID_DATA,
                    detail="missing session bars",
                ),
            ),
        )

    all_bars = list(warmup_bars) + list(session_bars)
    min_required_warmup = max(
        settings.atr_period + settings.atr_ma_period,
        settings.ema_trend_period,
        settings.breakout_channel_bars,
    )

    if len(warmup_bars) < min_required_warmup:
        return ReplaySessionResult(
            session_day=session_day,
            outcome=SessionOutcome.INVALID_DATA,
            events=(
                SimulationEvent(
                    timestamp=session_bars[0].timestamp,
                    kind=SimulationEventKind.INVALID_DATA,
                    detail="insufficient prior warmup history",
                ),
            ),
        )

    # Compute indicators up to the start of the session
    atr_history: list[Decimal] = []
    ema_value: Decimal = all_bars[0].close
    alpha = Decimal("2") / Decimal(settings.ema_trend_period + 1)

    for i in range(1, len(all_bars)):
        cb = all_bars[i]
        pb = all_bars[i - 1]
        tr = max(cb.high - cb.low, abs(cb.high - pb.close), abs(cb.low - pb.close))
        ema_value = (cb.close * alpha) + (ema_value * (Decimal("1") - alpha))

        if i >= settings.atr_period:
            window = all_bars[i - settings.atr_period + 1 : i + 1]
            trs = [
                max(
                    window[j].high - window[j].low,
                    abs(window[j].high - window[j - 1].close),
                    abs(window[j].low - window[j - 1].close),
                )
                for j in range(1, len(window))
            ]
            trs.append(tr)
            atr_history.append(sum(trs) / Decimal(len(trs)))

    # Session trading loop
    in_position = False
    entry_side: str | None = None
    entry_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    risk_distance: Decimal | None = None
    slip = settings.additional_slippage_points * settings.point_size

    warmup_len = len(warmup_bars)

    for idx, bar in enumerate(session_bars):
        ny_time = bar.timestamp.astimezone(NEW_YORK).time()
        bar_idx_in_all = warmup_len + idx

        if not in_position:
            # Check entry eligibility within session window
            if settings.session_start_ny <= ny_time <= settings.session_end_ny:
                # Indicators available at prior bar close
                recent_channel = all_bars[
                    bar_idx_in_all - settings.breakout_channel_bars : bar_idx_in_all
                ]
                channel_high = max(b.high for b in recent_channel)
                channel_low = min(b.low for b in recent_channel)

                current_atr = (
                    atr_history[bar_idx_in_all - settings.atr_period]
                    if len(atr_history) > (bar_idx_in_all - settings.atr_period)
                    else Decimal("1.5")
                )
                atr_slice = atr_history[
                    max(
                        0, bar_idx_in_all - settings.atr_period - settings.atr_ma_period
                    ) : bar_idx_in_all - settings.atr_period
                ]
                atr_ma = (
                    sum(atr_slice) / Decimal(len(atr_slice))
                    if atr_slice
                    else current_atr
                )

                spread = Decimal(bar.spread_points or 2) * settings.point_size

                # Long Entry Condition: Volatility expanding & Trend bullish & Breakout high
                if (
                    current_atr >= atr_ma
                    and bar.high > channel_high
                    and bar.close > ema_value
                ):
                    in_position = True
                    entry_side = "buy"
                    entry_price = (
                        max(channel_high + settings.point_size, bar.open)
                        + (spread / Decimal("2"))
                        + slip
                    )
                    risk_distance = max(current_atr, settings.min_stop_distance)
                    stop_loss = entry_price - risk_distance
                    take_profit = entry_price + (
                        risk_distance * settings.risk_reward_ratio
                    )
                    events.append(
                        SimulationEvent(
                            timestamp=bar.timestamp,
                            kind=SimulationEventKind.ENTRY_FILLED,
                            detail=f"Candidate 007 BUY filled at {entry_price}",
                            price=entry_price,
                        )
                    )
                    continue

                # Short Entry Condition: Volatility expanding & Trend bearish & Breakout low
                elif (
                    current_atr >= atr_ma
                    and bar.low < channel_low
                    and bar.close < ema_value
                ):
                    in_position = True
                    entry_side = "sell"
                    entry_price = (
                        min(channel_low - settings.point_size, bar.open)
                        - (spread / Decimal("2"))
                        - slip
                    )
                    risk_distance = max(current_atr, settings.min_stop_distance)
                    stop_loss = entry_price + risk_distance
                    take_profit = entry_price - (
                        risk_distance * settings.risk_reward_ratio
                    )
                    events.append(
                        SimulationEvent(
                            timestamp=bar.timestamp,
                            kind=SimulationEventKind.ENTRY_FILLED,
                            detail=f"Candidate 007 SELL filled at {entry_price}",
                            price=entry_price,
                        )
                    )
                    continue

        else:
            # We are in an active position; evaluate stop, target, or session close
            assert entry_price is not None
            assert stop_loss is not None
            assert take_profit is not None
            assert risk_distance is not None

            if entry_side == "buy":
                hit_stop = bar.low <= stop_loss
                hit_target = bar.high >= take_profit

                if hit_stop and hit_target:
                    # Ambiguous bar: both stop and target touched in one M1 bar
                    return ReplaySessionResult(
                        session_day=session_day,
                        outcome=SessionOutcome.AMBIGUOUS,
                        events=tuple(events),
                    )
                if hit_stop:
                    exit_price = stop_loss - slip
                    r_mult = (exit_price - entry_price) / risk_distance
                    events.append(
                        SimulationEvent(
                            timestamp=bar.timestamp,
                            kind=SimulationEventKind.STOP_FILLED,
                            detail=f"Buy stop filled at {exit_price}",
                            price=exit_price,
                        )
                    )
                    return ReplaySessionResult(
                        session_day=session_day,
                        outcome=SessionOutcome.STOPPED_OUT,
                        events=tuple(events),
                        entry_side="buy",
                        entry_price=entry_price,
                        exit_price=exit_price,
                        r_multiple=r_mult,
                    )
                if hit_target:
                    exit_price = take_profit - slip
                    r_mult = (exit_price - entry_price) / risk_distance
                    events.append(
                        SimulationEvent(
                            timestamp=bar.timestamp,
                            kind=SimulationEventKind.FORCED_EXIT,
                            detail=f"Buy 2R target filled at {exit_price}",
                            price=exit_price,
                        )
                    )
                    return ReplaySessionResult(
                        session_day=session_day,
                        outcome=SessionOutcome.FORCED_EXIT,
                        events=tuple(events),
                        entry_side="buy",
                        entry_price=entry_price,
                        exit_price=exit_price,
                        r_multiple=r_mult,
                    )

            elif entry_side == "sell":
                hit_stop = bar.high >= stop_loss
                hit_target = bar.low <= take_profit

                if hit_stop and hit_target:
                    return ReplaySessionResult(
                        session_day=session_day,
                        outcome=SessionOutcome.AMBIGUOUS,
                        events=tuple(events),
                    )
                if hit_stop:
                    exit_price = stop_loss + slip
                    r_mult = (entry_price - exit_price) / risk_distance
                    events.append(
                        SimulationEvent(
                            timestamp=bar.timestamp,
                            kind=SimulationEventKind.STOP_FILLED,
                            detail=f"Sell stop filled at {exit_price}",
                            price=exit_price,
                        )
                    )
                    return ReplaySessionResult(
                        session_day=session_day,
                        outcome=SessionOutcome.STOPPED_OUT,
                        events=tuple(events),
                        entry_side="sell",
                        entry_price=entry_price,
                        exit_price=exit_price,
                        r_multiple=r_mult,
                    )
                if hit_target:
                    exit_price = take_profit + slip
                    r_mult = (entry_price - exit_price) / risk_distance
                    events.append(
                        SimulationEvent(
                            timestamp=bar.timestamp,
                            kind=SimulationEventKind.FORCED_EXIT,
                            detail=f"Sell 2R target filled at {exit_price}",
                            price=exit_price,
                        )
                    )
                    return ReplaySessionResult(
                        session_day=session_day,
                        outcome=SessionOutcome.FORCED_EXIT,
                        events=tuple(events),
                        entry_side="sell",
                        entry_price=entry_price,
                        exit_price=exit_price,
                        r_multiple=r_mult,
                    )

            # Session end exit (13:30 NY)
            if ny_time >= settings.exit_time_ny:
                exit_price = bar.close + (slip if entry_side == "sell" else -slip)
                if entry_side == "buy":
                    r_mult = (exit_price - entry_price) / risk_distance
                else:
                    r_mult = (entry_price - exit_price) / risk_distance

                events.append(
                    SimulationEvent(
                        timestamp=bar.timestamp,
                        kind=SimulationEventKind.FORCED_EXIT,
                        detail=f"Session time exit at {exit_price}",
                        price=exit_price,
                    )
                )
                return ReplaySessionResult(
                    session_day=session_day,
                    outcome=SessionOutcome.FORCED_EXIT,
                    events=tuple(events),
                    entry_side=entry_side,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    r_multiple=r_mult,
                )

    if in_position:
        # End of available bars in session without touching stop/target
        assert entry_price is not None
        assert risk_distance is not None
        last_bar = session_bars[-1]
        exit_price = last_bar.close
        r_mult = (
            (exit_price - entry_price)
            if entry_side == "buy"
            else (entry_price - exit_price)
        ) / risk_distance
        return ReplaySessionResult(
            session_day=session_day,
            outcome=SessionOutcome.FORCED_EXIT,
            events=tuple(events),
            entry_side=entry_side,
            entry_price=entry_price,
            exit_price=exit_price,
            r_multiple=r_mult,
        )

    return ReplaySessionResult(
        session_day=session_day,
        outcome=SessionOutcome.NO_TRADE,
        events=(
            SimulationEvent(
                timestamp=session_bars[0].timestamp,
                kind=SimulationEventKind.DIRECTIONAL_BIAS_NO_TRADE,
                detail="no eligible breakout during active session window",
            ),
        ),
    )
