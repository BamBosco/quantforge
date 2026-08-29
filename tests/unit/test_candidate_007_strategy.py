"""Unit tests for Candidate 007 Volatility Regime & Trend-Filtered Strategy."""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from quantforge.application.trading_pipeline import MarketFact
from quantforge.backtest.models import MinuteBar
from quantforge.strategies.candidate_007 import (
    Candidate007Settings,
    Candidate007Strategy,
)

NEW_YORK = ZoneInfo("America/New_York")


def make_bar(
    timestamp: datetime,
    close: str,
    high: str | None = None,
    low: str | None = None,
    open_: str | None = None,
) -> MinuteBar:
    c = Decimal(close)
    h = Decimal(high) if high is not None else c + Decimal("0.5")
    low_val = Decimal(low) if low is not None else c - Decimal("0.5")
    o = Decimal(open_) if open_ is not None else c
    return MinuteBar(timestamp, o, h, low_val, c, tick_volume=10, spread_points=2)


def make_market_fact(
    observed_at: datetime,
    bid: str = "2400.00",
    ask: str = "2400.20",
    instrument: str = "XAUUSD",
) -> MarketFact:
    return MarketFact(
        instrument=instrument,
        bid=Decimal(bid),
        ask=Decimal(ask),
        observed_at=observed_at,
        value_per_price_unit_per_lot=Decimal("100"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
    )


def test_candidate_007_initialization_defaults() -> None:
    strat = Candidate007Strategy()
    assert strat.strategy_id == "candidate_007_volatility_regime_trend"
    assert strat.version == "0.1"
    assert strat.settings.risk_reward_ratio == Decimal("2.0")
    assert strat.settings.atr_period == 14
    assert strat.settings.ema_trend_period == 50


def test_candidate_007_ignores_when_warmup_incomplete() -> None:
    strat = Candidate007Strategy()
    # Provide only 5 bars (insufficient warmup)
    base = datetime(2026, 8, 28, 9, 0, tzinfo=NEW_YORK)
    for i in range(5):
        strat.update_bar(make_bar(base + timedelta(minutes=i), "2400.00"))

    market = make_market_fact(observed_at=base + timedelta(minutes=6))
    signal = strat.evaluate(market, evaluated_at=base + timedelta(minutes=6))
    assert signal is None


def test_candidate_007_ignores_outside_session_hours() -> None:
    strat = Candidate007Strategy()
    # Feed 70 warmup bars
    base = datetime(2026, 8, 28, 6, 0, tzinfo=NEW_YORK)
    for i in range(70):
        strat.update_bar(make_bar(base + timedelta(minutes=i), "2400.00"))

    # Evaluated at 07:30 NY (before 08:30 NY open)
    market = make_market_fact(observed_at=datetime(2026, 8, 28, 7, 30, tzinfo=NEW_YORK))
    signal = strat.evaluate(
        market, evaluated_at=datetime(2026, 8, 28, 7, 30, tzinfo=NEW_YORK)
    )
    assert signal is None


def test_candidate_007_emits_buy_signal_on_breakout_and_trend() -> None:
    strat = Candidate007Strategy()
    # Upward trending warmup bars to build bullish EMA and high ATR
    start = datetime(2026, 8, 28, 6, 0, tzinfo=NEW_YORK)
    for i in range(70):
        price = Decimal("2380.00") + (Decimal(str(i)) * Decimal("0.3"))
        strat.update_bar(
            make_bar(
                start + timedelta(minutes=i),
                close=str(price),
                high=str(price + Decimal("2.0")),
                low=str(price - Decimal("2.0")),
            )
        )

    # Trigger a breakout above the 20-bar channel high during active session
    eval_time = datetime(2026, 8, 28, 9, 15, tzinfo=NEW_YORK)
    market = make_market_fact(
        observed_at=eval_time,
        bid="2410.00",
        ask="2410.20",
    )

    signal = strat.evaluate(market, evaluated_at=eval_time)
    assert signal is not None
    assert signal.side == "buy"
    assert signal.instrument == "XAUUSD"
    assert signal.entry_price == Decimal("2410.20")
    assert signal.stop_loss_price < signal.entry_price
    # Check 2R target distance: (target - entry) == 2 * (entry - stop)
    risk = signal.entry_price - signal.stop_loss_price
    reward = signal.target_price - signal.entry_price
    assert reward == risk * Decimal("2.0")


def test_candidate_007_enforces_one_trade_per_day() -> None:
    strat = Candidate007Strategy()
    start = datetime(2026, 8, 28, 6, 0, tzinfo=NEW_YORK)
    for i in range(70):
        price = Decimal("2380.00") + (Decimal(str(i)) * Decimal("0.3"))
        strat.update_bar(
            make_bar(
                start + timedelta(minutes=i),
                close=str(price),
                high=str(price + Decimal("2.0")),
                low=str(price - Decimal("2.0")),
            )
        )

    eval_time_1 = datetime(2026, 8, 28, 9, 15, tzinfo=NEW_YORK)
    signal_1 = strat.evaluate(
        make_market_fact(observed_at=eval_time_1, bid="2410.00", ask="2410.20"),
        evaluated_at=eval_time_1,
    )
    assert signal_1 is not None

    # Immediate second quote on same day must be rejected (1 trade/day limit)
    eval_time_2 = datetime(2026, 8, 28, 9, 20, tzinfo=NEW_YORK)
    signal_2 = strat.evaluate(
        make_market_fact(observed_at=eval_time_2, bid="2415.00", ask="2415.20"),
        evaluated_at=eval_time_2,
    )
    assert signal_2 is None


def test_candidate_007_fails_closed_on_invalid_market() -> None:
    strat = Candidate007Strategy()
    # Missing timezone or inverted bid/ask
    bad_quote = MarketFact(
        instrument="XAUUSD",
        bid=Decimal("2400.00"),
        ask=Decimal("2399.00"),  # Inverted spread
        observed_at=datetime(2026, 8, 28, 9, 15, tzinfo=NEW_YORK),
        value_per_price_unit_per_lot=Decimal("100"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
    )
    signal = strat.evaluate(bad_quote, evaluated_at=bad_quote.observed_at)
    assert signal is None


def test_candidate_007_micro_scalper_multi_trade() -> None:
    settings = Candidate007Settings.for_btcusd_scalper()
    strat = Candidate007Strategy(settings=settings)

    start = datetime(2026, 8, 29, 10, 0, tzinfo=NEW_YORK)
    # Warmup 40 bars (enough for atr=14, atr_ma=20, ema=30, channel=15)
    for i in range(40):
        price = Decimal("77500.00") + (Decimal(str(i)) * Decimal("2.0"))
        strat.update_bar(
            make_bar(
                start + timedelta(minutes=i),
                close=str(price),
                high=str(price + Decimal("5.0")),
                low=str(price - Decimal("5.0")),
            )
        )

    # First scalp signal
    eval_time_1 = start + timedelta(minutes=41)
    sig1 = strat.evaluate(
        make_market_fact(
            observed_at=eval_time_1, bid="77650.00", ask="77655.00", instrument="BTCUSD"
        ),
        evaluated_at=eval_time_1,
    )
    assert sig1 is not None
    assert sig1.side == "buy"

    # Advance 6 bars (pass cooldown of 5 bars)
    for j in range(42, 48):
        price = Decimal("77650.00") + (Decimal(str(j)) * Decimal("2.0"))
        strat.update_bar(
            make_bar(
                start + timedelta(minutes=j),
                close=str(price),
                high=str(price + Decimal("5.0")),
                low=str(price - Decimal("5.0")),
            )
        )

    # Second scalp signal allowed!
    eval_time_2 = start + timedelta(minutes=48)
    sig2 = strat.evaluate(
        make_market_fact(
            observed_at=eval_time_2, bid="77800.00", ask="77805.00", instrument="BTCUSD"
        ),
        evaluated_at=eval_time_2,
    )
    assert sig2 is not None
    assert sig2.side == "buy"
