from __future__ import annotations

from pathlib import Path

import pytest

from quantforge.config.settings import load_forex_mt5_demo_settings
from quantforge.infrastructure.mt5.demo_submission_stage_b import (
    DemoSubmissionDisabled,
    MT5DemoSubmissionGateway,
)


def gateway() -> MT5DemoSubmissionGateway:
    return MT5DemoSubmissionGateway(
        load_forex_mt5_demo_settings(Path("config/forex_mt5_demo_usdjpy.toml"))
    )


def stage_a_request(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "stage": "A",
        "broker_symbol": "USDJPY",
        "send_allowed": False,
        "submission_status": "prohibited_stage_a",
    }
    value.update(changes)
    return value


def test_stage_b_is_unconditionally_disabled_for_demo_profile() -> None:
    assert gateway().submission_enabled is False


def test_valid_stage_a_request_is_still_refused_before_submission() -> None:
    with pytest.raises(DemoSubmissionDisabled, match="Stage B submission is disabled"):
        gateway().submit(stage_a_request())


def test_invalid_stage_a_provenance_is_reported_without_external_action() -> None:
    reasons = gateway().validate_disabled_request(
        stage_a_request(stage="B", send_allowed=True)
    )

    assert "request was not constructed by Stage A" in reasons
    assert "Stage A request must prohibit sending" in reasons
    assert "Stage B submission is disabled pending separate authorisation" in reasons
