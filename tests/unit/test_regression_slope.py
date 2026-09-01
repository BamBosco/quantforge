"""Unit tests for the Regression Slope Oscillator (QuantAlgo)."""

from decimal import Decimal

import pytest

from quantforge.analytics.regression_slope import (
    MomentumRegime,
    RegressionSlopeOscillator,
    calculate_ols_slope,
    calculate_theil_sen_slope,
)


def test_ols_slope_calculation() -> None:
    # Linear upward trend: y = 2x + 10 -> [10, 12, 14, 16, 18]
    prices = [Decimal("10"), Decimal("12"), Decimal("14"), Decimal("16"), Decimal("18")]
    slope = calculate_ols_slope(prices)
    assert slope == Decimal("2")

    # Flat line: [5, 5, 5]
    flat = [Decimal("5"), Decimal("5"), Decimal("5")]
    assert calculate_ols_slope(flat) == Decimal("0")

    # Empty and single value edge cases
    assert calculate_ols_slope([]) == Decimal("0")
    assert calculate_ols_slope([Decimal("100")]) == Decimal("0")


def test_theil_sen_robust_slope() -> None:
    # Upward trend with a single outlier noise spike: [10, 12, 999, 16, 18]
    prices_with_outlier = [
        Decimal("10"),
        Decimal("12"),
        Decimal("999"),  # Extreme wick/bad tick
        Decimal("16"),
        Decimal("18"),
    ]
    # Theil-Sen median slope should be close to 2.0 despite the extreme outlier
    robust_slope = calculate_theil_sen_slope(prices_with_outlier)
    assert Decimal("1.5") <= robust_slope <= Decimal("2.5")

    # Clean linear sequence
    clean = [Decimal("10"), Decimal("12"), Decimal("14"), Decimal("16"), Decimal("18")]
    assert calculate_theil_sen_slope(clean) == Decimal("2")


def test_oscillator_warmup_and_streaming() -> None:
    osc = RegressionSlopeOscillator(period=5, norm_period=5)

    # Initial feeds under lookback period should return Neutral
    for p in [100, 102, 104, 106]:
        snap = osc.update(p)
        assert snap.regime == MomentumRegime.NEUTRAL
        assert snap.raw_slope == Decimal("0")

    # 5th price point completes warmup window
    snap = osc.update(108)
    assert snap.raw_slope > Decimal("0")
    assert snap.is_bullish is True
    assert snap.is_bearish is False


def test_oscillator_bearish_regime() -> None:
    osc = RegressionSlopeOscillator(period=5, norm_period=5, neutral_threshold=Decimal("0.1"))

    # Feed downward trend
    for p in range(100, 80, -2):
        snap = osc.update(p)

    assert snap.raw_slope < Decimal("0")
    assert snap.is_bearish is True
    assert snap.regime in {
        MomentumRegime.BEARISH_ACCELERATING,
        MomentumRegime.BEARISH_DECELERATING,
    }


def test_oscillator_invalid_parameters() -> None:
    with pytest.raises(ValueError, match="period must be at least 2"):
        RegressionSlopeOscillator(period=1)

    with pytest.raises(ValueError, match="norm_period must be at least 2"):
        RegressionSlopeOscillator(norm_period=1)
