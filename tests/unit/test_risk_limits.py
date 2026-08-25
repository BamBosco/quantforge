"""Tests for central pre-trade risk limits and risk-owned position sizing."""

from decimal import Decimal

from quantforge.risk.limits import (
    AccountRiskSnapshot,
    RiskLimits,
    SizingRequest,
    assess_pre_trade_risk,
)


def limits() -> RiskLimits:
    return RiskLimits(
        Decimal("0.01"), Decimal("0.03"), Decimal("0.06"), Decimal("0.03")
    )


def snapshot(**changes: Decimal) -> AccountRiskSnapshot:
    values = {
        "current_equity": Decimal("10000"),
        "start_of_day_equity": Decimal("10000"),
        "peak_equity": Decimal("10000"),
        "correlated_open_risk": Decimal("0"),
    }
    values.update(changes)
    return AccountRiskSnapshot(**values)


def request(**changes: Decimal | str) -> SizingRequest:
    values = {
        "side": "buy",
        "entry_price": Decimal("100"),
        "stop_loss_price": Decimal("99"),
        "value_per_price_unit_per_lot": Decimal("100"),
        "minimum_volume": Decimal("0.01"),
        "maximum_volume": Decimal("100"),
        "volume_step": Decimal("0.01"),
    }
    values.update(changes)
    return SizingRequest(**values)


def test_risk_engine_sizes_to_the_configured_trade_budget() -> None:
    decision = assess_pre_trade_risk(request(), snapshot(), limits())

    assert decision.approved
    assert decision.quantity == Decimal("1")
    assert decision.proposed_risk == Decimal("100")


def test_daily_drawdown_requires_kill_switch_and_rejects_intent() -> None:
    decision = assess_pre_trade_risk(
        request(), snapshot(current_equity=Decimal("9700")), limits()
    )

    assert not decision.approved
    assert decision.kill_switch_required
    assert decision.reasons == ("daily drawdown limit breached",)


def test_correlated_open_risk_cannot_exceed_configured_limit() -> None:
    decision = assess_pre_trade_risk(
        request(), snapshot(correlated_open_risk=Decimal("250")), limits()
    )

    assert not decision.approved
    assert decision.reasons == ("correlated open-risk limit would be exceeded",)
