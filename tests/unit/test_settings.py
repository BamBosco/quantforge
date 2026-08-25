from pathlib import Path

from quantforge.config.settings import load_settings


def test_default_configuration_is_research_only() -> None:
    root = Path(__file__).parents[2]

    settings = load_settings(root / "config" / "default.toml")

    assert settings.runtime.live_trading_enabled is False
    assert settings.runtime.trading_mode == "research"
