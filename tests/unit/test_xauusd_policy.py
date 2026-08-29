from decimal import Decimal
from pathlib import Path

import pytest

from quantforge.config.xauusd_policy import (
    XAUUSDRiskPolicyConfigurationError,
    load_xauusd_risk_policy,
)


def write_policy(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


def test_loads_explicit_policy(tmp_path: Path) -> None:
    path = write_policy(
        tmp_path / "policy.toml",
        "[risk]\nrisk_per_trade = 0.01\nmaximum_position_size = 2.5\n",
    )
    result = load_xauusd_risk_policy(path)
    assert result.risk_per_trade == Decimal("0.01")
    assert result.maximum_position_size == Decimal("2.5")


@pytest.mark.parametrize(
    "content, expected",
    [
        ("", "risk must be a TOML table"),
        (
            "[risk]\nrisk_per_trade = 0.01\n",
            "maximum_position_size must be explicitly configured",
        ),
        (
            "[risk]\nmaximum_position_size = 2\n",
            "risk_per_trade must be explicitly configured",
        ),
        (
            "[risk]\nrisk_per_trade = 0\nmaximum_position_size = 2\n",
            "risk_per_trade must be greater than zero",
        ),
        (
            "[risk]\nrisk_per_trade = 1.01\nmaximum_position_size = 2\n",
            "risk_per_trade must be greater than zero",
        ),
        (
            "[risk]\nrisk_per_trade = 0.01\nmaximum_position_size = 0\n",
            "maximum_position_size must be greater than zero",
        ),
        (
            '[risk]\nrisk_per_trade = "NaN"\nmaximum_position_size = 2\n',
            "risk_per_trade must be a finite number",
        ),
    ],
)
def test_policy_never_invents_or_inherits_values(
    tmp_path: Path, content: str, expected: str
) -> None:
    path = write_policy(tmp_path / "policy.toml", content)
    with pytest.raises(XAUUSDRiskPolicyConfigurationError, match=expected):
        load_xauusd_risk_policy(path)
