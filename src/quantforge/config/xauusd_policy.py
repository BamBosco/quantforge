"""Explicit Candidate 006 XAUUSD risk-policy loading."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


class XAUUSDRiskPolicyConfigurationError(ValueError):
    """Raised when Candidate 006 risk policy is missing or unsafe."""


@dataclass(frozen=True, slots=True)
class XAUUSDRiskPolicyConfig:
    """Explicit XAUUSD risk policy with no inherited defaults."""

    risk_per_trade: Decimal
    maximum_position_size: Decimal


def load_xauusd_risk_policy(path: Path) -> XAUUSDRiskPolicyConfig:
    """Load a complete XAUUSD risk policy and reject unsafe values."""
    with path.open("rb") as file:
        raw = tomllib.load(file)
    table = raw.get("risk")
    if not isinstance(table, dict):
        raise XAUUSDRiskPolicyConfigurationError("risk must be a TOML table")
    risk_per_trade = _decimal(table.get("risk_per_trade"), "risk_per_trade")
    maximum_position_size = _decimal(
        table.get("maximum_position_size"), "maximum_position_size"
    )
    if not 0 < risk_per_trade <= 1:
        raise XAUUSDRiskPolicyConfigurationError(
            "risk_per_trade must be greater than zero and at most one"
        )
    if maximum_position_size <= 0:
        raise XAUUSDRiskPolicyConfigurationError(
            "maximum_position_size must be greater than zero"
        )
    return XAUUSDRiskPolicyConfig(risk_per_trade, maximum_position_size)


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise XAUUSDRiskPolicyConfigurationError(
            f"{name} must be explicitly configured"
        )
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise XAUUSDRiskPolicyConfigurationError(
            f"{name} must be a finite number"
        ) from error
    if not decimal.is_finite():
        raise XAUUSDRiskPolicyConfigurationError(f"{name} must be a finite number")
    return decimal
