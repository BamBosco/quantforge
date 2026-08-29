"""Independent Risk Limits and Pre-Trade Sizing Gate.

Enforces loss circuit breakers, position limits, protective stop validation,
and maximum open position constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Literal

from quantforge.risk.validation import validate_protective_stop


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """Explicit parameters governing loss ceilings and sizing limits."""

    risk_per_trade: Decimal
    max_daily_drawdown: Decimal
    max_total_drawdown: Decimal
    max_correlated_open_risk: Decimal
    allow_micro_lot_clamp: bool = False

    def __post_init__(self) -> None:
        for field_name, value in (
            ("risk_per_trade", self.risk_per_trade),
            ("max_daily_drawdown", self.max_daily_drawdown),
            ("max_total_drawdown", self.max_total_drawdown),
            ("max_correlated_open_risk", self.max_correlated_open_risk),
        ):
            if value <= 0 or value > Decimal("1.0"):
                raise ValueError(f"{field_name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class SizingRequest:
    """Pre-trade facts required to compute an approved quantity."""

    side: Literal["buy", "sell"]
    entry_price: Decimal
    stop_loss_price: Decimal
    value_per_price_unit_per_lot: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal

    def __post_init__(self) -> None:
        if self.entry_price <= 0 or self.stop_loss_price <= 0:
            raise ValueError("entry and stop loss prices must be positive")
        if self.value_per_price_unit_per_lot <= 0:
            raise ValueError("value per price unit must be positive")
        if (
            self.minimum_volume <= 0
            or self.maximum_volume < self.minimum_volume
            or self.volume_step <= 0
        ):
            raise ValueError("invalid broker volume bounds")


@dataclass(frozen=True, slots=True)
class AccountRiskSnapshot:
    """Account state required for pre-trade risk evaluation."""

    current_equity: Decimal
    start_of_day_equity: Decimal
    peak_equity: Decimal
    correlated_open_risk: Decimal

    def __post_init__(self) -> None:
        if (
            self.current_equity < 0
            or self.start_of_day_equity <= 0
            or self.peak_equity <= 0
        ):
            raise ValueError("account snapshot equity figures must be valid")


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """Result of evaluating a sizing request against risk limits."""

    approved: bool
    reasons: tuple[str, ...]
    quantity: Decimal | None = None
    proposed_risk: Decimal | None = None
    kill_switch_required: bool = False


def assess_pre_trade_risk(
    request: SizingRequest,
    snapshot: AccountRiskSnapshot,
    limits: RiskLimits,
) -> RiskDecision:
    """Apply loss halts, sizing, and concentration limits."""
    reasons: list[str] = []
    stop_validation = validate_protective_stop(
        request.side, request.entry_price, request.stop_loss_price
    )
    if not stop_validation.approved:
        reasons.extend(stop_validation.reasons)

    if _daily_drawdown(snapshot) >= limits.max_daily_drawdown:
        reasons.append("daily drawdown limit breached")
    if _total_drawdown(snapshot) >= limits.max_total_drawdown:
        reasons.append("total drawdown limit breached")

    kill_switch_required = any(
        "drawdown limit breached" in reason for reason in reasons
    )
    if reasons:
        return RiskDecision(
            False, tuple(reasons), kill_switch_required=kill_switch_required
        )

    risk_per_lot = abs(request.entry_price - request.stop_loss_price) * (
        request.value_per_price_unit_per_lot
    )
    if risk_per_lot <= 0:
        return RiskDecision(False, ("risk per lot must be positive",))

    risk_budget = snapshot.current_equity * limits.risk_per_trade
    calculated_qty = _snap_down(risk_budget / risk_per_lot, request.volume_step)
    if calculated_qty < request.minimum_volume:
        if limits.allow_micro_lot_clamp and snapshot.current_equity > 0:
            calculated_qty = request.minimum_volume
        else:
            reasons.append("risk budget cannot support minimum volume")
            return RiskDecision(False, tuple(reasons))

    quantity = min(calculated_qty, request.maximum_volume)
    proposed_risk = quantity * risk_per_lot
    total_correlated_risk = snapshot.correlated_open_risk + proposed_risk
    if (
        total_correlated_risk
        > snapshot.current_equity * limits.max_correlated_open_risk
        and not (
            limits.allow_micro_lot_clamp
            and quantity == request.minimum_volume
            and snapshot.correlated_open_risk == 0
        )
    ):
        reasons.append("correlated open-risk limit would be exceeded")
        return RiskDecision(False, tuple(reasons))

    return RiskDecision(True, (), quantity=quantity, proposed_risk=proposed_risk)


def _daily_drawdown(snapshot: AccountRiskSnapshot) -> Decimal:
    return max(
        Decimal("0"),
        (snapshot.start_of_day_equity - snapshot.current_equity)
        / snapshot.start_of_day_equity,
    )


def _total_drawdown(snapshot: AccountRiskSnapshot) -> Decimal:
    return max(
        Decimal("0"),
        (snapshot.peak_equity - snapshot.current_equity) / snapshot.peak_equity,
    )


def _snap_down(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step
