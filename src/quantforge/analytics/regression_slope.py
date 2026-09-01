"""Regression Slope Oscillator (QuantAlgo) for QuantForge.

Computes a scale-free, outlier-resistant linear regression price slope
and classifies real-time momentum into directional acceleration regimes.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Final


class MomentumRegime(StrEnum):
    """Directional momentum state derived from slope and slope delta."""

    BULLISH_ACCELERATING = "bullish_accelerating"
    BULLISH_DECELERATING = "bullish_decelerating"
    BEARISH_ACCELERATING = "bearish_accelerating"
    BEARISH_DECELERATING = "bearish_decelerating"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class RegressionSlopeSnapshot:
    """Immutable point-in-time calculation of regression slope and regime."""

    raw_slope: Decimal
    normalized_score: Decimal
    slope_delta: Decimal
    regime: MomentumRegime
    is_bullish: bool
    is_bearish: bool


def calculate_ols_slope(prices: Sequence[Decimal]) -> Decimal:
    """Calculate Ordinary Least Squares (OLS) slope for a sequence of prices.
    
    x-coordinates are assumed to be 0, 1, 2, ..., n-1.
    """
    n = len(prices)
    if n < 2:
        return Decimal("0")

    dec_n = Decimal(str(n))
    x_mean = Decimal(str(n - 1)) / Decimal("2")
    y_mean = sum(prices) / dec_n

    numerator = Decimal("0")
    denominator = Decimal("0")

    for i, y in enumerate(prices):
        x_diff = Decimal(str(i)) - x_mean
        y_diff = y - y_mean
        numerator += x_diff * y_diff
        denominator += x_diff * x_diff

    if denominator == Decimal("0"):
        return Decimal("0")

    return numerator / denominator


def calculate_theil_sen_slope(prices: Sequence[Decimal]) -> Decimal:
    """Calculate median pairwise slope (Theil-Sen estimator) for robust outlier resistance."""
    n = len(prices)
    if n < 2:
        return Decimal("0")

    slopes: list[Decimal] = []
    for i in range(n):
        for j in range(i + 1, n):
            dx = Decimal(str(j - i))
            dy = prices[j] - prices[i]
            slopes.append(dy / dx)

    if not slopes:
        return Decimal("0")

    slopes.sort()
    mid = len(slopes) // 2
    if len(slopes) % 2 == 1:
        return slopes[mid]
    return (slopes[mid - 1] + slopes[mid]) / Decimal("2")


class RegressionSlopeOscillator:
    """Streaming, real-time Regression Slope Oscillator with rolling normalization."""

    def __init__(
        self,
        period: int = 14,
        norm_period: int = 20,
        use_robust_estimator: bool = True,
        neutral_threshold: Decimal = Decimal("0.15"),
    ) -> None:
        if period < 2:
            raise ValueError("period must be at least 2")
        if norm_period < 2:
            raise ValueError("norm_period must be at least 2")

        self.period: Final = period
        self.norm_period: Final = norm_period
        self.use_robust_estimator: Final = use_robust_estimator
        self.neutral_threshold: Final = neutral_threshold

        self._price_buffer: deque[Decimal] = deque(maxlen=period)
        self._raw_slope_history: deque[Decimal] = deque(maxlen=norm_period)
        self._prev_slope: Decimal | None = None

    def update(self, price: Decimal | float | int | str) -> RegressionSlopeSnapshot:
        """Feed a new price tick or bar close and compute the snapshot."""
        dec_price = Decimal(str(price))
        self._price_buffer.append(dec_price)

        if len(self._price_buffer) < self.period:
            return RegressionSlopeSnapshot(
                raw_slope=Decimal("0"),
                normalized_score=Decimal("0"),
                slope_delta=Decimal("0"),
                regime=MomentumRegime.NEUTRAL,
                is_bullish=False,
                is_bearish=False,
            )

        # 1. Calculate raw slope
        prices = list(self._price_buffer)
        if self.use_robust_estimator:
            raw_slope = calculate_theil_sen_slope(prices)
        else:
            raw_slope = calculate_ols_slope(prices)

        self._raw_slope_history.append(raw_slope)

        # 2. Calculate slope delta (rate of slope change / second derivative)
        slope_delta = (
            raw_slope - self._prev_slope
            if self._prev_slope is not None
            else Decimal("0")
        )
        self._prev_slope = raw_slope

        # 3. Calculate scale-free normalized score
        if len(self._raw_slope_history) >= 2:
            slope_list = list(self._raw_slope_history)
            mean_slope = sum(slope_list) / Decimal(len(slope_list))
            variance = sum((s - mean_slope) ** 2 for s in slope_list) / Decimal(
                len(slope_list)
            )
            std_dev = Decimal(str(float(variance) ** 0.5))
            if std_dev > Decimal("0"):
                norm_score = raw_slope / std_dev
            elif raw_slope > Decimal("0"):
                norm_score = Decimal("3.0")
            elif raw_slope < Decimal("0"):
                norm_score = Decimal("-3.0")
            else:
                norm_score = Decimal("0")
        else:
            if raw_slope > Decimal("0"):
                norm_score = Decimal("1.0")
            elif raw_slope < Decimal("0"):
                norm_score = Decimal("-1.0")
            else:
                norm_score = Decimal("0")

        # Clamp normalized score between -3.0 and +3.0 standard deviations
        clamped_score = max(Decimal("-3.0"), min(Decimal("3.0"), norm_score))


        # 4. Classify momentum regime
        if abs(clamped_score) < self.neutral_threshold:
            regime = MomentumRegime.NEUTRAL
        elif clamped_score > Decimal("0"):
            if slope_delta >= Decimal("0"):
                regime = MomentumRegime.BULLISH_ACCELERATING
            else:
                regime = MomentumRegime.BULLISH_DECELERATING
        else:
            if slope_delta <= Decimal("0"):
                regime = MomentumRegime.BEARISH_ACCELERATING
            else:
                regime = MomentumRegime.BEARISH_DECELERATING

        is_bullish = regime in {
            MomentumRegime.BULLISH_ACCELERATING,
            MomentumRegime.BULLISH_DECELERATING,
        }
        is_bearish = regime in {
            MomentumRegime.BEARISH_ACCELERATING,
            MomentumRegime.BEARISH_DECELERATING,
        }

        return RegressionSlopeSnapshot(
            raw_slope=raw_slope,
            normalized_score=clamped_score,
            slope_delta=slope_delta,
            regime=regime,
            is_bullish=is_bullish,
            is_bearish=is_bearish,
        )
