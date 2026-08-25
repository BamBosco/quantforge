from datetime import datetime, timedelta
from decimal import Decimal

from quantforge.backtest.models import MinuteBar, OpeningRange
from quantforge.backtest.orb import NEW_YORK, OPENING_TIME
from quantforge.backtest.orb_bias import EntryEligibility
from quantforge.backtest.orb_simulation import (
    OrbSimulationSettings,
    SessionOutcome,
    SimulationEventKind,
    simulate_orb_session,
)


def settings() -> OrbSimulationSettings:
    return OrbSimulationSettings(
        point_size=Decimal("0.01"), additional_slippage_points=Decimal("0")
    )


def prior_ranges() -> list[OpeningRange]:
    return [
        OpeningRange(Decimal("101"), Decimal("99"), Decimal("100"))
        for _ in range(10)
    ]


def session_bars() -> list[MinuteBar]:
    start = datetime(
        2026,
        8,
        14,
        OPENING_TIME.hour,
        OPENING_TIME.minute,
        tzinfo=NEW_YORK,
    )
    bars = []
    for offset in range(311):
        timestamp = start + timedelta(minutes=offset)
        high = Decimal("100")
        low = Decimal("100")
        if offset == 0:
            high = Decimal("101")
            low = Decimal("99")
        bars.append(
            MinuteBar(
                timestamp=timestamp,
                open=Decimal("100"),
                high=high,
                low=low,
                close=Decimal("100"),
                tick_volume=1,
                spread_points=0,
            )
        )
    return bars


def replace_bar(bars: list[MinuteBar], offset: int, **changes: Decimal) -> None:
    original = bars[offset]
    bars[offset] = MinuteBar(
        timestamp=original.timestamp,
        open=changes.get("open", original.open),
        high=changes.get("high", original.high),
        low=changes.get("low", original.low),
        close=changes.get("close", original.close),
        tick_volume=original.tick_volume,
        spread_points=original.spread_points,
    )


def test_fills_one_oco_entry_then_forces_exit() -> None:
    bars = session_bars()
    replace_bar(bars, 15, high=Decimal("103"), low=Decimal("100"), close=Decimal("102"))
    replace_bar(
        bars,
        310,
        open=Decimal("104"),
        high=Decimal("104"),
        low=Decimal("104"),
        close=Decimal("104"),
    )

    result = simulate_orb_session(
        bars,
        session_day=datetime(2026, 8, 14).date(),
        prior_ranges=prior_ranges(),
        settings=settings(),
    )

    assert result.outcome is SessionOutcome.FORCED_EXIT
    assert result.entry_side == "buy"
    assert result.entry_price == Decimal("102")
    assert result.exit_price == Decimal("104")
    assert result.r_multiple == Decimal("0.5")
    assert [event.kind for event in result.events] == [
        SimulationEventKind.RANGE_COMPLETED,
        SimulationEventKind.RISK_APPROVED,
        SimulationEventKind.ENTRY_FILLED,
        SimulationEventKind.OCO_CANCELED,
        SimulationEventKind.FORCED_EXIT,
    ]


def test_marks_same_bar_oco_touches_as_ambiguous() -> None:
    bars = session_bars()
    replace_bar(bars, 15, high=Decimal("103"), low=Decimal("97"))

    result = simulate_orb_session(
        bars,
        session_day=datetime(2026, 8, 14).date(),
        prior_ranges=prior_ranges(),
        settings=settings(),
    )

    assert result.outcome is SessionOutcome.AMBIGUOUS
    assert result.events[-1].kind is SimulationEventKind.AMBIGUOUS


def test_fills_protective_stop_after_oco_peer_is_canceled() -> None:
    bars = session_bars()
    replace_bar(bars, 15, high=Decimal("103"), low=Decimal("100"))
    replace_bar(bars, 16, high=Decimal("101"), low=Decimal("97"))

    result = simulate_orb_session(
        bars,
        session_day=datetime(2026, 8, 14).date(),
        prior_ranges=prior_ranges(),
        settings=settings(),
    )

    assert result.outcome is SessionOutcome.STOPPED_OUT
    assert result.exit_price == Decimal("98")
    assert result.r_multiple == Decimal("-1")
    assert result.events[-1].kind is SimulationEventKind.STOP_FILLED


def test_rejects_session_with_a_missing_minute_before_forced_exit() -> None:
    bars = session_bars()
    del bars[60]

    result = simulate_orb_session(
        bars,
        session_day=datetime(2026, 8, 14).date(),
        prior_ranges=prior_ranges(),
        settings=settings(),
    )

    assert result.outcome is SessionOutcome.INVALID_DATA
    assert result.events[-1].kind is SimulationEventKind.INVALID_DATA


def test_directional_neutral_session_records_no_trade_without_order() -> None:
    result = simulate_orb_session(
        session_bars(),
        session_day=datetime(2026, 8, 14).date(),
        prior_ranges=prior_ranges(),
        settings=settings(),
        entry_eligibility=EntryEligibility(
            frozenset(), "directional bias is neutral: no eligible entry"
        ),
    )

    assert result.outcome is SessionOutcome.NO_TRADE
    assert [event.kind for event in result.events] == [
        SimulationEventKind.RANGE_COMPLETED,
        SimulationEventKind.DIRECTIONAL_BIAS_NO_TRADE,
    ]


def test_marks_directional_entry_and_protective_stop_same_bar_as_ambiguous() -> None:
    bars = session_bars()
    replace_bar(bars, 15, high=Decimal("103"), low=Decimal("97"))

    result = simulate_orb_session(
        bars,
        session_day=datetime(2026, 8, 14).date(),
        prior_ranges=prior_ranges(),
        settings=settings(),
        entry_eligibility=EntryEligibility(
            frozenset({"buy"}), "overnight bias is long"
        ),
    )

    assert result.outcome is SessionOutcome.AMBIGUOUS
    assert result.events[-1].kind is SimulationEventKind.AMBIGUOUS
