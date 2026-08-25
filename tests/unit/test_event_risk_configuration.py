from pathlib import Path

from quantforge.config.event_risk import load_event_risk_policy


def test_loads_xauusd_scheduled_event_policy() -> None:
    settings = load_event_risk_policy(
        Path("config/risk/xauusd_scheduled_event_policy.toml")
    )

    assert settings.blackout_before_event.total_seconds() == 3 * 60 * 60
    assert "US_CPI" in settings.covered_event_types["XAUUSD"]
    assert settings.requires_manual_post_event_release is True
