"""Pure pre-trade limits and position sizing owned solely by the Risk Engine."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

from quantforge.config.settings import RiskSettings
from quantforge.risk.validation import validate_protective_stop


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """Configured account-level limits expressed as fractions of equity."""

    risk_per_trade: Decimal
    max_daily_drawdown: Decimal
    max_total_drawdown: Decimal
    max_correlated_open_risk: Decimal

    def __post_init__(self) -> None:
        for value in (
            self.risk_per_trade,
            self.max_daily_drawdown,
            self.max_total_drawdown,
            self.max_correlated_open_risk,
        ):
            if not Decimal("0") < value <= Decimal("1"):
                raise ValueError(
                    "risk limits must be greater than zero and at most one"
                )


@dataclass(frozen=True, slots=True)
class AccountRiskSnapshot:
    """Portfolio facts required for a non-bypassable risk decision."""

    current_equity: Decimal
    start_of_day_equity: Decimal
    peak_equity: Decimal
    correlated_open_risk: Decimal

    def __post_init__(self) -> None:
        if self.current_equity <= 0 or self.start_of_day_equity <= 0:
            raise ValueError("equity values must be positive")
        if self.peak_equity < self.current_equity:
            raise ValueError("peak equity cannot be below current equity")
        if self.correlated_open_risk < 0:
            raise ValueError("correlated open risk must not be negative")


@dataclass(frozen=True, slots=True)
class SizingRequest:
    """Unsized intent facts and broker volume constraints for risk calculation."""

    side: str
    entry_price: Decimal
    stop_loss_price: Decimal
    value_per_price_unit_per_lot: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal

    def __post_init__(self) -> None:
        if self.value_per_price_unit_per_lot <= 0:
            raise ValueError("value per price unit must be positive")
        if self.minimum_volume <= 0 or self.maximum_volume < self.minimum_volume:
            raise ValueError("broker volume bounds are invalid")
        if self.volume_step <= 0:
            raise ValueError("broker volume step must be positive")


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """Non-executable result; only an approved decision may be converted to an order."""

    approved: bool
    reasons: tuple[str, ...]
    quantity: Decimal | None = None
    proposed_risk: Decimal | None = None
    kill_switch_required: bool = False


def limits_from_settings(settings: RiskSettings) -> RiskLimits:
    """Convert TOML float values explicitly before monetary risk math begins."""
    return RiskLimits(
        risk_per_trade=Decimal(str(settings.risk_per_trade)),
        max_daily_drawdown=Decimal(str(settings.max_daily_drawdown)),
        max_total_drawdown=Decimal(str(settings.max_total_drawdown)),
        max_correlated_open_risk=Decimal(str(settings.max_correlated_open_risk)),
    )


def assess_pre_trade_risk(
    request: SizingRequest,
    snapshot: AccountRiskSnapshot,
    limits: RiskLimits,
) -> RiskDecision:
    """Apply loss halts, sizing, and concentration limits before any approval."""
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
    quantity = _snap_down(risk_budget / risk_per_lot, request.volume_step)
    quantity = min(quantity, request.maximum_volume)
    if quantity < request.minimum_volume:
        return RiskDecision(
            False,
            ("risk budget is smaller than the broker minimum volume",),
        )
    proposed_risk = quantity * risk_per_lot
    concentration_limit = snapshot.current_equity * limits.max_correlated_open_risk
    if snapshot.correlated_open_risk + proposed_risk > concentration_limit:
        return RiskDecision(False, ("correlated open-risk limit would be exceeded",))
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
