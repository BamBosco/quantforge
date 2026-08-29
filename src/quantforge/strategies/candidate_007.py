"""Candidate 007 Volatility Expansion, Trend Filter & Market Structure Strategy.

Supports Higher Highs / Higher Lows (HH/HL) and Lower Lows / Lower Highs (LL/LH)
market structure confirmation with dynamic structural profit exits for Gold (XAUUSD) & BTCUSD.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Final, Literal
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from quantforge.application.trading_pipeline import MarketFact, TradingSignal
from quantforge.backtest.models import MinuteBar

NEW_YORK: Final = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class Candidate007Settings:
    """Configurable hyperparameters for Candidate 007 with Market Structure."""

    instrument: str = "XAUUSD"
    atr_period: int = 14
    atr_ma_period: int = 20
    ema_trend_period: int = 50
    breakout_channel_bars: int = 20
    structure_bars: int = 5
    risk_reward_ratio: Decimal = Decimal("2.0")
    min_stop_distance: Decimal = Decimal("1.5")
    allow_weekend_trading: bool = False
    max_trades_per_day: int = 1
    cooldown_bars: int = 15
    session_start_ny: time = time(8, 30)
    session_end_ny: time = time(12, 30)
    exit_time_ny: time = time(13, 30)

    @classmethod
    def for_btcusd(cls) -> Candidate007Settings:
        """Patient trend settings for BTCUSD weekend forward testing."""
        return cls(
            instrument="BTCUSD",
            atr_period=14,
            atr_ma_period=20,
            ema_trend_period=50,
            breakout_channel_bars=20,
            structure_bars=5,
            risk_reward_ratio=Decimal("2.0"),
            min_stop_distance=Decimal("85.0"),
            allow_weekend_trading=True,
            max_trades_per_day=1,
            session_start_ny=time(0, 0),
            session_end_ny=time(23, 59),
            exit_time_ny=time(23, 59),
        )

    @classmethod
    def for_hybrid_dynamic_scalper(
        cls, instrument: str = "XAUUSD"
    ) -> Candidate007Settings:
        """Hybrid Dynamic Scalper with Active Micro-Profit Banking.

        Features:
        - Rapid turnover: 10 to 20 trades per day during active volume.
        - Dynamic Profit Target: +zsh.80 to +.50 per trade.
        - Tight Structural Invalidation Stop: -zsh.80 to -.00 (1:1.5 R:R).
        - Active Windows: London & New York Sessions (07:00 - 16:30 UTC).
        """
        is_btc = "BTC" in instrument.upper()
        return cls(
            instrument=instrument,
            atr_period=7,
            atr_ma_period=14,
            ema_trend_period=20,
            breakout_channel_bars=7,
            structure_bars=3,
            risk_reward_ratio=Decimal("1.5"),
            min_stop_distance=Decimal("85.0") if is_btc else Decimal("0.80"),
            allow_weekend_trading=is_btc,
            max_trades_per_day=20,
            cooldown_bars=2,
            session_start_ny=time(0, 0) if is_btc else time(7, 0),
            session_end_ny=time(23, 59) if is_btc else time(16, 30),
            exit_time_ny=time(23, 59) if is_btc else time(17, 0),
        )

    @classmethod
    def for_new_york_gold_scalper(cls) -> Candidate007Settings:
        """Active Session Scalper for XAUUSD Gold (New York Session)."""
        return cls.for_gold_active_scalper()

    @classmethod
    def for_gold_active_scalper(cls) -> Candidate007Settings:
        """Active High-Frequency SMC & Volatility Scalper preset for Gold (XAUUSD)."""
        return cls(
            instrument="XAUUSD",
            atr_period=7,
            atr_ma_period=14,
            ema_trend_period=20,
            breakout_channel_bars=7,
            structure_bars=3,
            risk_reward_ratio=Decimal("2.5"),
            min_stop_distance=Decimal("1.20"),
            allow_weekend_trading=False,
            max_trades_per_day=25,
            cooldown_bars=2,
            session_start_ny=time(7, 0),
            session_end_ny=time(16, 0),
            exit_time_ny=time(16, 30),
        )

    @classmethod
    def for_btcusd_scalper(cls) -> Candidate007Settings:
        """High-Activity Micro-Scalper preset for BTCUSD with tight SL and far 2.5R TP."""
        return cls(
            instrument="BTCUSD",
            atr_period=14,
            atr_ma_period=20,
            ema_trend_period=30,
            breakout_channel_bars=15,
            structure_bars=4,
            risk_reward_ratio=Decimal("2.5"),
            min_stop_distance=Decimal("100.0"),
            allow_weekend_trading=True,
            max_trades_per_day=15,
            cooldown_bars=5,
            session_start_ny=time(0, 0),
            session_end_ny=time(23, 59),
            exit_time_ny=time(23, 59),
        )

    @classmethod
    def for_xauusd(cls) -> Candidate007Settings:
        """Optimal settings for XAUUSD Gold weekday trading with Market Structure (1:2.5R)."""
        return cls(
            instrument="XAUUSD",
            atr_period=14,
            atr_ma_period=20,
            ema_trend_period=50,
            breakout_channel_bars=20,
            structure_bars=5,
            risk_reward_ratio=Decimal("2.5"),
            min_stop_distance=Decimal("1.20"),
            allow_weekend_trading=False,
            max_trades_per_day=5,
            cooldown_bars=3,
            session_start_ny=time(8, 30),
            session_end_ny=time(16, 30),
            exit_time_ny=time(17, 0),
        )


class Candidate007Strategy:
    """Strategy combining ATR expansion, EMA trend filter, and HH/HL / LL/LH market structure."""

    strategy_id = "candidate_007_volatility_regime_trend"
    version = "0.1"

    def __init__(self, settings: Candidate007Settings | None = None) -> None:
        self.settings = settings or Candidate007Settings()
        self._daily_trade_counts: dict[str, int] = {}
        self._bars_since_last_trade: int = 999
        self._bars: deque[MinuteBar] = deque(maxlen=200)
        self._atr_history: deque[Decimal] = deque(maxlen=100)
        self._ema_value: Decimal | None = None

    def update_bar(self, bar: MinuteBar) -> None:
        """Update internal bar buffer and indicator series with a completed M1 bar."""
        prev_bar = self._bars[-1] if self._bars else None
        self._bars.append(bar)
        self._bars_since_last_trade += 1

        # 1. Update True Range & ATR
        if prev_bar is not None:
            hl = bar.high - bar.low
            hc = abs(bar.high - prev_bar.close)
            lc = abs(bar.low - prev_bar.close)
            tr = max(hl, hc, lc)
        else:
            tr = bar.high - bar.low

        if len(self._bars) >= self.settings.atr_period:
            recent_bars = list(self._bars)[-self.settings.atr_period :]
            trs = []
            for i in range(1, len(recent_bars)):
                pb = recent_bars[i - 1]
                cb = recent_bars[i]
                trs.append(
                    max(
                        cb.high - cb.low,
                        abs(cb.high - pb.close),
                        abs(cb.low - pb.close),
                    )
                )
            trs.append(tr)
            current_atr = sum(trs) / Decimal(len(trs))
            self._atr_history.append(current_atr)

        # 2. Update Trend EMA
        alpha = Decimal("2") / Decimal(self.settings.ema_trend_period + 1)
        if self._ema_value is None:
            self._ema_value = bar.close
        else:
            self._ema_value = (bar.close * alpha) + (
                self._ema_value * (Decimal("1") - alpha)
            )

    def evaluate(
        self, market: MarketFact, *, evaluated_at: datetime
    ) -> TradingSignal | None:
        """Evaluate market with Market Structure (HH/HL for Buy, LL/LH for Sell)."""
        if not self._valid_market(market):
            return None

        session_time = market.observed_at.astimezone(NEW_YORK)
        date_key = session_time.date().isoformat()
        current_time = session_time.time()

        # Weekend filter (disabled for 24/7 crypto like BTCUSD)
        if not self.settings.allow_weekend_trading and session_time.weekday() > 4:
            return None

        # Session timing check
        if not (
            self.settings.session_start_ny
            <= current_time
            <= self.settings.session_end_ny
        ):
            return None

        # Daily trade limit & Cooldown check
        if (
            self._daily_trade_counts.get(date_key, 0)
            >= self.settings.max_trades_per_day
        ):
            return None
        if self._bars_since_last_trade < self.settings.cooldown_bars:
            return None

        # Indicator readiness check
        if len(self._bars) < max(
            self.settings.atr_period + self.settings.atr_ma_period,
            self.settings.ema_trend_period,
            self.settings.breakout_channel_bars + 1,
        ):
            return None

        if not self._atr_history or self._ema_value is None:
            return None

        current_atr = self._atr_history[-1]
        if len(self._atr_history) >= self.settings.atr_ma_period:
            atr_ma = sum(
                list(self._atr_history)[-self.settings.atr_ma_period :]
            ) / Decimal(self.settings.atr_ma_period)
        else:
            atr_ma = sum(self._atr_history) / Decimal(len(self._atr_history))

        # 1. Volatility Expansion Gate
        if current_atr < atr_ma:
            return None

        # 2. Donchian Breakout Channel over PRIOR completed bars
        channel_bars = list(self._bars)[:-1][-self.settings.breakout_channel_bars :]
        channel_high = max(b.high for b in channel_bars)
        channel_low = min(b.low for b in channel_bars)

        # 3. Market Structure Analysis (HH/HL and LL/LH)
        recent_struct_bars = list(self._bars)[-self.settings.structure_bars :]
        is_bullish_structure = False
        is_bearish_structure = False

        if len(recent_struct_bars) >= 2:
            # Bullish structure: Higher Highs and Higher Lows
            higher_highs = recent_struct_bars[-1].high >= recent_struct_bars[-2].high
            higher_lows = recent_struct_bars[-1].low >= recent_struct_bars[-2].low
            is_bullish_structure = higher_highs and higher_lows

            # Bearish structure: Lower Lows and Lower Highs
            lower_lows = recent_struct_bars[-1].low <= recent_struct_bars[-2].low
            lower_highs = recent_struct_bars[-1].high <= recent_struct_bars[-2].high
            is_bearish_structure = lower_lows and lower_highs

        side: Literal["buy", "sell"] | None = None
        entry_price: Decimal = Decimal("0")
        stop_loss: Decimal = Decimal("0")
        target_price: Decimal = Decimal("0")
        stop_dist = max(current_atr * Decimal("1.5"), self.settings.min_stop_distance)

        # 4. Long Condition: Channel Breakout + Bullish Structure (HH/HL) + Above 50 EMA
        if (
            market.ask > channel_high
            and market.bid > self._ema_value
            and (is_bullish_structure or not self.settings.structure_bars)
        ):
            side = "buy"
            entry_price = market.ask
            # Structural swing stop placed safely below the Higher Low
            lowest_swing = min(b.low for b in recent_struct_bars)
            stop_loss = min(
                lowest_swing - (current_atr * Decimal("0.5")), entry_price - stop_dist
            )
            target_price = entry_price + (
                abs(entry_price - stop_loss) * self.settings.risk_reward_ratio
            )

        # 5. Short Condition: Channel Breakout + Bearish Structure (LL/LH) + Below 50 EMA
        elif (
            market.bid < channel_low
            and market.ask < self._ema_value
            and (is_bearish_structure or not self.settings.structure_bars)
        ):
            side = "sell"
            entry_price = market.bid
            # Structural swing stop placed safely above the Lower High
            highest_swing = max(b.high for b in recent_struct_bars)
            stop_loss = max(
                highest_swing + (current_atr * Decimal("0.5")), entry_price + stop_dist
            )
            target_price = entry_price - (
                abs(stop_loss - entry_price) * self.settings.risk_reward_ratio
            )

        if side is None:
            return None

        self._daily_trade_counts[date_key] = (
            self._daily_trade_counts.get(date_key, 0) + 1
        )
        self._bars_since_last_trade = 0
        trade_num = self._daily_trade_counts[date_key]

        scheduled_exit = datetime.combine(
            session_time.date(), self.settings.exit_time_ny, tzinfo=NEW_YORK
        ).astimezone(UTC)

        struct_desc = (
            "HH/HL Bullish Structure" if side == "buy" else "LL/LH Bearish Structure"
        )

        return TradingSignal(
            strategy_id=self.strategy_id,
            instrument=market.instrument,
            side=side,
            entry_price=entry_price,
            stop_loss_price=stop_loss,
            target_price=target_price,
            scheduled_exit_at=scheduled_exit,
            rationale=(
                f"Candidate 007 Trend #{trade_num} {side.upper()} on {market.instrument}: "
                f"{struct_desc}, ATR expansion ({current_atr:.2f} >= {atr_ma:.2f}), "
                f"EMA trend ({market.bid:.2f} vs {self._ema_value:.2f}), "
                f"{self.settings.risk_reward_ratio}R target ({target_price:.2f})"
            ),
            signal_id=uuid5(
                NAMESPACE_URL,
                f"{self.strategy_id}:{self.version}:{market.instrument}:{date_key}:{trade_num}:{side}:{entry_price}",
            ),
        )

    def _valid_market(self, market: MarketFact) -> bool:
        norm_expected = self.settings.instrument.strip("#._/ ").replace("/", "").upper()
        norm_market = market.instrument.strip("#._/ ").replace("/", "").upper()
        return bool(
            (
                market.instrument == self.settings.instrument
                or norm_market == norm_expected
            )
            and market.observed_at.tzinfo is not None
            and market.observed_at.utcoffset() is not None
            and market.bid > 0
            and market.ask >= market.bid
        )
