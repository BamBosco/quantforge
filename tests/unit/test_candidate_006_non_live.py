from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from quantforge.application.experimental_paper_demo import demo_observation
from quantforge.config.xauusd_research_stage_a import (
    load_xauusd_research_stage_a_settings,
)
from quantforge.infrastructure.mt5.candidate_006_non_live import (
    assess_candidate_006_non_live_readiness,
    persist_candidate_006_non_live_readiness,
)
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog


def _settings():
    return load_xauusd_research_stage_a_settings(
        Path(__file__).parents[2]
        / "config"
        / "candidate_006_xauusd_research_stage_a.toml"
    )


def _observation(at: datetime):
    result = demo_observation(
        observed_at=at, bid=Decimal("4600"), ask=Decimal("4600.5")
    )
    payload = result.payload
    payload["source"] = {"adapter": "mt5", "broker_profile_id": "dukascopy-demo"}
    payload["account"]["server"] = "Dukascopy-demo-mt5-1"
    payload["instrument"]["broker_symbol"] = "XAUUSD"
    payload["quote"]["spread_points"] = 500
    payload["instrument"]["specification"].update(
        {"trade_calculation_mode": 0, "profit_currency": "USD"}
    )
    return type(result).from_payload(payload)


def test_persists_receipt_linked_non_live_readiness(tmp_path: Path) -> None:
    now = datetime(2026, 8, 26, 13, tzinfo=UTC)
    observation = _observation(now)
    readiness = assess_candidate_006_non_live_readiness(
        observation=observation, settings=_settings(), evaluated_at=now
    )
    assert readiness.status == "ready_non_live"
    assert readiness.artifact["send_allowed"] is False
    assert readiness.artifact["submission_status"] == "prohibited_stage_a"
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    try:
        assert persist_candidate_006_non_live_readiness(log, readiness) is True
        assert persist_candidate_006_non_live_readiness(log, readiness) is False
        stored = log.candidate_006_non_live_readiness(observation.observation_id)
        assert stored is not None
        assert stored["status"] == "ready_non_live"
        assert stored["artifact"]["order_submission_enabled"] is False
    finally:
        log.close()


def test_rejects_stale_or_excessive_spread_receipt() -> None:
    now = datetime(2026, 8, 26, 13, tzinfo=UTC)
    observation = _observation(now - timedelta(minutes=1))
    observation.payload["quote"]["spread_points"] = 761
    readiness = assess_candidate_006_non_live_readiness(
        observation=observation, settings=_settings(), evaluated_at=now
    )
    assert readiness.status == "not_ready"
    assert "receipt is not fresh" in readiness.checks
    assert "spread exceeds provisional research cap" in readiness.checks


def test_accepts_a_utc_receipt_despite_a_non_utc_host_display_timezone() -> None:
    """Freshness compares UTC instants, never a local wall-clock rendering."""
    observed_at = datetime(2026, 8, 26, 10, 16, 2, tzinfo=UTC)
    readiness = assess_candidate_006_non_live_readiness(
        observation=_observation(observed_at),
        settings=_settings(),
        evaluated_at=datetime(2026, 8, 26, 10, 16, 26, tzinfo=UTC),
    )
    assert readiness.status == "ready_non_live"
    assert "fresh observation" in readiness.checks
