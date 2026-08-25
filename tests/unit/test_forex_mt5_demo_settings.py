from pathlib import Path

import pytest

from quantforge.config.settings import (
    ForexMT5DemoConfigurationError,
    load_forex_mt5_demo_settings,
)


def test_usdjpy_demo_profile_is_closed_candle_and_non_executable() -> None:
    root = Path(__file__).parents[2]

    settings = load_forex_mt5_demo_settings(
        root / "config" / "forex_mt5_demo_usdjpy.toml"
    )

    assert settings.instrument.internal_symbol == "USDJPY"
    assert settings.instrument.broker_symbol == "USDJPY"
    assert settings.instrument.timeframe == "M1"
    assert settings.instrument.closed_candles_only is True
    assert settings.execution.account_mode == "demo"
    assert settings.execution.live_trading_enabled is False
    assert settings.execution.order_submission_enabled is False
    assert settings.risk.broker_lot_constraints_source == "mt5_symbol_info"


@pytest.mark.parametrize(
    ("replacement", "error"),
    [
        ("closed_candles_only = false", "closed_candles_only must be true"),
        ("account_mode = \"live\"", "account_mode must be demo"),
        ("live_trading_enabled = true", "live trading is prohibited"),
        ("order_submission_enabled = true", "Phase 1 cannot enable order submission"),
        ("max_open_positions = 2", "max_open_positions must be exactly one"),
    ],
)
def test_unsafe_demo_profile_is_rejected(
    tmp_path: Path, replacement: str, error: str
) -> None:
    root = Path(__file__).parents[2]
    profile = (root / "config" / "forex_mt5_demo_usdjpy.toml").read_text()
    original = replacement.split(" = ")[0] + " = "
    line = next(line for line in profile.splitlines() if line.startswith(original))
    unsafe_profile = profile.replace(line, replacement)
    path = tmp_path / "unsafe.toml"
    path.write_text(unsafe_profile)

    with pytest.raises(ForexMT5DemoConfigurationError, match=error):
        load_forex_mt5_demo_settings(path)
