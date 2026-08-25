from pathlib import Path

import pytest

from quantforge.config.settings import (
    ForexMT5DemoConfigurationError,
    load_forex_mt5_demo_settings,
    load_xauusd_read_only_broker_profile,
)


def test_xauusd_uses_a_separate_read_only_scope() -> None:
    root = Path(__file__).parents[2]
    profile = load_xauusd_read_only_broker_profile(
        root / "config" / "candidate_006_xauusd_read_only.toml"
    )
    assert profile.broker_venue == "Dukascopy"
    assert profile.internal_symbol == profile.broker_symbol == "XAUUSD"
    assert profile.timeframe == "M1"
    assert (
        profile.audit_journal_path
        == "data/candidate_006_xauusd/xauusd_m1_demo.sqlite3"
    )
    assert profile.order_submission_enabled is False


def test_xauusd_rejects_non_dukascopy_broker_identity(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    text = (root / "config" / "candidate_006_xauusd_read_only.toml").read_text()
    path = tmp_path / "profile.toml"
    path.write_text(text.replace('venue = "Dukascopy"', 'venue = "Headway"'))
    with pytest.raises(
        ForexMT5DemoConfigurationError, match="broker contract is invalid"
    ):
        load_xauusd_read_only_broker_profile(path)


def test_usdjpy_profile_remains_unchanged() -> None:
    root = Path(__file__).parents[2]
    profile = load_forex_mt5_demo_settings(
        root / "config" / "forex_mt5_demo_usdjpy.toml"
    )
    assert profile.instrument.internal_symbol == "USDJPY"
    assert profile.risk.max_spread_points == 20


def test_xauusd_missing_risk_or_spread_policy_cannot_fall_back(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[2]
    text = (root / "config" / "candidate_006_xauusd_read_only.toml").read_text()
    path = tmp_path / "profile.toml"
    path.write_text(text.replace('  "maximum_spread_policy",\n', ""))
    with pytest.raises(
        ForexMT5DemoConfigurationError,
        match="unresolved requirements are incomplete",
    ):
        load_xauusd_read_only_broker_profile(path)


@pytest.mark.parametrize(
    "usd_jpy_policy",
    (
        "max_spread_points = 20",
        "max_position_size = 1",
    ),
)
def test_xauusd_rejects_usdjpy_risk_policy_fields(
    tmp_path: Path, usd_jpy_policy: str
) -> None:
    root = Path(__file__).parents[2]
    text = (root / "config" / "candidate_006_xauusd_read_only.toml").read_text()
    path = tmp_path / "profile.toml"
    path.write_text(text + f"\n[risk]\n{usd_jpy_policy}\n")
    with pytest.raises(ForexMT5DemoConfigurationError, match="cannot inherit risk"):
        load_xauusd_read_only_broker_profile(path)


@pytest.mark.parametrize(
    "broker_fact",
    (
        "digits = 2",
        "point = 0.01",
        "contract_size = 100",
        "volume_min = 0.01",
        "volume_max = 100",
        "volume_step = 0.01",
    ),
)
def test_xauusd_broker_facts_must_come_from_mt5_observations(
    tmp_path: Path, broker_fact: str
) -> None:
    root = Path(__file__).parents[2]
    text = (root / "config" / "candidate_006_xauusd_read_only.toml").read_text()
    path = tmp_path / "profile.toml"
    path.write_text(
        text.replace('timeframe = "M1"', f'timeframe = "M1"\n{broker_fact}')
    )
    with pytest.raises(ForexMT5DemoConfigurationError, match="must be observed"):
        load_xauusd_read_only_broker_profile(path)


def test_xauusd_profile_has_no_execution_capability() -> None:
    root = Path(__file__).parents[2]
    profile = load_xauusd_read_only_broker_profile(
        root / "config" / "candidate_006_xauusd_read_only.toml"
    )
    assert profile.demo_only is True
    assert profile.order_submission_enabled is False
