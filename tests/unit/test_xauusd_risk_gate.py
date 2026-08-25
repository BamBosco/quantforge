from decimal import Decimal

import pytest

from quantforge.risk.xauusd_gate import XAUUSDRiskGate, XAUUSDRiskPolicy


def metadata(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "symbol": "XAUUSD",
        "account_currency": "USD",
        "profit_currency": "USD",
        "trade_calculation_mode": 0,
        "tick_size": 0.001,
        "tick_value_loss": 0.1,
        "volume_min": 0.01,
        "volume_max": 10000,
        "volume_step": 0.01,
    }
    value.update(changes)
    return value


def policy() -> XAUUSDRiskPolicy:
    return XAUUSDRiskPolicy(Decimal("0.01"), Decimal("100"))


def intent(direction: str = "BUY", **changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "direction": direction,
        "entry_price": 2000,
        "stop_loss": 1999,
        "take_profit": 2002,
    }
    if direction == "SELL":
        value.update({"stop_loss": 2001, "take_profit": 1998})
    value.update(changes)
    return value


def evaluate(**changes: object):
    args = {
        "trade_intent": intent(),
        "broker_metadata": metadata(),
        "account_equity": Decimal("10000"),
        "policy": policy(),
    }
    args.update(changes)
    return XAUUSDRiskGate().evaluate(**args)


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_valid_xauusd_sizing(direction: str) -> None:
    result = evaluate(trade_intent=intent(direction))
    assert result.status == "approved" and result.proposed_volume == Decimal("1")
    assert result.proposed_risk_usd == Decimal("100")


def test_tick_calculation_and_step_rounding() -> None:
    result = evaluate(
        trade_intent=intent(stop_loss=1999.767),
        account_equity=Decimal("101"),
        policy=XAUUSDRiskPolicy(Decimal("1"), Decimal("100")),
    )
    assert result.proposed_volume == Decimal("4.33")
    assert result.proposed_risk_usd == Decimal("100.889")


@pytest.mark.parametrize(
    "equity,maximum,reason",
    [("1", "100", "minimum volume"), ("10000", "0.005", "minimum volume")],
)
def test_volume_constraints(equity: str, maximum: str, reason: str) -> None:
    result = evaluate(
        account_equity=Decimal(equity),
        policy=XAUUSDRiskPolicy(Decimal("0.01"), Decimal(maximum)),
    )
    assert result.status == "rejected" and reason in result.reasons[0]


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_invalid_protective_levels(direction: str) -> None:
    invalid = {"stop_loss": 2001, "take_profit": 1999}
    if direction == "SELL":
        invalid = {"stop_loss": 1999, "take_profit": 2001}
    result = evaluate(trade_intent=intent(direction, **invalid))
    assert f"invalid {direction} protective levels" in result.reasons


def test_missing_policies_fail_closed() -> None:
    result = evaluate(policy=XAUUSDRiskPolicy())
    assert result.reasons == (
        "Candidate 006 risk-per-trade policy is unresolved",
        "Candidate 006 maximum-position policy is unresolved",
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"symbol": "USDJPY"},
        {"account_currency": "JPY"},
        {"profit_currency": "JPY"},
        {"tick_size": 0},
    ],
)
def test_rejects_wrong_or_missing_broker_facts(changes: dict[str, object]) -> None:
    assert evaluate(broker_metadata=metadata(**changes)).status == "rejected"


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"entry_price": 2000, "stop_loss": 2000}, "entry and stop_loss must differ"),
        ({"entry_price": 2000, "stop_loss": 1999, "take_profit": 2001}, None),
    ],
)
def test_entry_stop_edge_cases(
    changes: dict[str, object], reason: str | None
) -> None:
    result = evaluate(trade_intent=intent(**changes))
    if reason is None:
        assert result.status == "approved"
    else:
        assert reason in result.reasons


@pytest.mark.parametrize("risk_fraction", ["0", "1.01", "-0.1"])
def test_risk_fraction_must_be_bounded(risk_fraction: str) -> None:
    result = evaluate(
        policy=XAUUSDRiskPolicy(Decimal(risk_fraction), Decimal("100"))
    )
    assert (
        "risk-per-trade policy must be greater than zero and at most one"
        in result.reasons
    )


@pytest.mark.parametrize("value", ["nan", "Infinity", "-Infinity"])
def test_non_finite_numeric_values_fail_closed(value: str) -> None:
    result = evaluate(
        broker_metadata=metadata(tick_size=value),
    )
    assert result.status == "rejected"


def test_audit_payload_is_non_executable() -> None:
    assert evaluate().audit_payload()["non_executable"] is True
