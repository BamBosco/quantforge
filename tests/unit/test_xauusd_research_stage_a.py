from datetime import UTC, datetime
from pathlib import Path

import pytest

from quantforge.config.xauusd_research_stage_a import (
    XAUUSDResearchStageAConfigurationError,
    load_xauusd_research_stage_a_settings,
)
from quantforge.infrastructure.mt5.xauusd_research_stage_a import (
    XAUUSDResearchStageAGateway,
)

NOW = datetime(2026, 8, 26, 13, tzinfo=UTC)


def settings():
    return load_xauusd_research_stage_a_settings(
        Path(__file__).parents[2]
        / "config"
        / "candidate_006_xauusd_research_stage_a.toml"
    )


def snapshot(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "instrument": {"canonical_instrument": "XAUUSD", "specification": {}},
        "quote": {"bid": "4600.000", "ask": "4600.500", "spread_points": 500},
    }
    value.update(changes)
    return value


def intent(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "symbol": "XAUUSD",
        "direction": "BUY",
        "entry_price": "4600.500",
    }
    value.update(changes)
    return value


def risk(volume: str = "0.01") -> dict[str, object]:
    return {
        "status": "approved",
        "risk_decision": {"proposed_volume": volume, "non_executable": True},
    }


def test_constructs_only_an_unsendable_research_artifact() -> None:
    result = XAUUSDResearchStageAGateway(settings()).construct(
        trade_intent=intent(),
        risk_decision=risk(),
        market_snapshot=snapshot(),
        evaluated_at=NOW,
    )

    assert result.status == "constructed"
    assert result.request is not None
    assert result.request["send_allowed"] is False
    assert result.request["submission_status"] == "prohibited_stage_a"
    assert result.request["execution_deviation_points"] == 0


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        (
            {"quote": {"bid": "4600", "ask": "4600.5", "spread_points": 761}},
            "spread exceeds",
        ),
        ({"entry_price": "4600.4"}, "zero-deviation"),
        ({"direction": "SELL", "entry_price": "4600.5"}, "zero-deviation"),
    ],
)
def test_rejects_unbounded_provisional_requests(
    changes: dict[str, object], reason: str
) -> None:
    result = XAUUSDResearchStageAGateway(settings()).construct(
        trade_intent=intent(**changes),
        risk_decision=risk("0.02" if "quote" not in changes else "0.01"),
        market_snapshot=snapshot(**changes),
        evaluated_at=NOW,
    )
    assert result.status == "rejected"
    assert any(reason in item for item in result.reasons)


def test_rejects_expired_provisional_profile() -> None:
    result = XAUUSDResearchStageAGateway(settings()).construct(
        trade_intent=intent(),
        risk_decision=risk(),
        market_snapshot=snapshot(),
        evaluated_at=datetime(2026, 9, 2, tzinfo=UTC),
    )
    assert "expired" in result.reasons[0]


def test_rejects_any_attempt_to_enable_submission(tmp_path: Path) -> None:
    original = (
        Path(__file__).parents[2]
        / "config"
        / "candidate_006_xauusd_research_stage_a.toml"
    ).read_text()
    invalid = tmp_path / "invalid.toml"
    invalid.write_text(
        original.replace(
            "order_submission_enabled = false", "order_submission_enabled = true"
        )
    )

    with pytest.raises(
        XAUUSDResearchStageAConfigurationError, match="must remain false"
    ):
        load_xauusd_research_stage_a_settings(invalid)
