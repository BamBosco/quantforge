from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quantforge.config.settings import load_forex_mt5_demo_settings
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.infrastructure.mt5.research_snapshot import (
    MT5ResearchSnapshotConsumer,
    ResearchSnapshotPolicy,
    policy_from_demo_settings,
)

NOW = datetime(2026, 8, 24, 16, 35, tzinfo=UTC)


def _observation(**changes: object) -> ObservationEnvelope:
    candle_time = NOW - timedelta(minutes=2)
    payload: dict[str, object] = {
        "schema_version": 2,
        "observed_at_utc": (NOW - timedelta(seconds=5)).isoformat(),
        "source": {
            "adapter": "mt5_read_only_ea",
            "broker_profile_id": "mt5_runtime_observed",
        },
        "account": {
            "account_id": "123",
            "server": "Dukascopy-Demo",
            "currency": "USD",
            "balance": 10_000.0,
            "equity": 10_000.0,
            "margin": 0.0,
            "free_margin": 10_000.0,
        },
        "instrument": {
            "canonical_instrument": "USDJPY",
            "broker_symbol": "USDJPY",
            "specification": {
                "point": 0.001,
                "digits": 3,
                "volume_min": 0.01,
                "volume_max": 100.0,
                "volume_step": 0.01,
                "contract_size": 100_000.0,
                "supported_filling_modes": ["fill_or_kill"],
            },
        },
        "quote": {
            "bid": 159.080, "ask": 159.082,
            "tick_time_utc": (NOW - timedelta(seconds=5)).isoformat(),
            "spread_points": 2.0,
        },
        "candles": {
            "timeframe": "M1", "forming": None,
            "completed": [{
                "open_time_utc": candle_time.isoformat(), "open": 159.070,
                "high": 159.085, "low": 159.065, "close": 159.080,
                "tick_volume": 25,
            }],
        },
        "positions": [], "active_orders": [],
        "deals": {
            "history_from_utc": (NOW - timedelta(seconds=5)).isoformat(),
            "history_to_utc": (NOW - timedelta(seconds=5)).isoformat(), "items": [],
        },
        "terminal": {"connected": True},
        "data_quality": {"adapter_status": "ok", "missing_data": []},
    }
    for path, value in changes.items():
        parent: dict[str, object] = payload
        parts = path.split(".")
        for part in parts[:-1]:
            nested = parent[part]
            assert isinstance(nested, dict)
            parent = nested
        parent[parts[-1]] = value
    return ObservationEnvelope.from_payload(payload)


def _consumer(
    tmp_path: Path,
) -> tuple[MT5ResearchSnapshotConsumer, SQLiteMarketObservationLog]:
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    return MT5ResearchSnapshotConsumer(log), log


def test_accepts_and_persists_fresh_closed_usdjpy_snapshot(tmp_path: Path) -> None:
    consumer, log = _consumer(tmp_path)
    try:
        result = consumer.consume(_observation(), evaluated_at=NOW)

        assert result.accepted
        assert result.snapshot is not None
        assert result.snapshot["candle"]["open_time_utc"].endswith("+00:00")
        assert result.snapshot["quote"]["spread_points"] == 2.0
        stored = log.research_snapshots()
        assert stored[0]["validation_status"] == "accepted"
        assert stored[0]["snapshot"]["instrument"]["broker_symbol"] == "USDJPY"
    finally:
        log.close()


def test_rejects_stale_observation_and_persists_reason(tmp_path: Path) -> None:
    consumer, log = _consumer(tmp_path)
    try:
        result = consumer.consume(
            _observation(observed_at_utc=(NOW - timedelta(seconds=91)).isoformat()),
            evaluated_at=NOW,
        )

        assert not result.accepted
        assert "observation is stale" in result.issues
        assert log.research_snapshots()[0]["validation_status"] == "rejected"
    finally:
        log.close()


def test_demo_profile_accepts_broker_supported_ioc(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    settings = load_forex_mt5_demo_settings(
        root / "config" / "forex_mt5_demo_usdjpy.toml"
    )
    consumer, log = _consumer(tmp_path)
    try:
        observation = _observation(
            **{
                "instrument.specification.supported_filling_modes": [
                    "immediate_or_cancel"
                ]
            }
        )
        configured = MT5ResearchSnapshotConsumer(
            log, policy=policy_from_demo_settings(settings)
        )

        assert settings.execution.filling_mode == "immediate_or_cancel"
        assert configured.consume(observation, evaluated_at=NOW).accepted
    finally:
        log.close()


def test_ioc_profile_rejects_broker_without_ioc(tmp_path: Path) -> None:
    consumer, log = _consumer(tmp_path)
    try:
        policy = ResearchSnapshotPolicy(required_filling_mode="immediate_or_cancel")
        result = MT5ResearchSnapshotConsumer(log, policy=policy).consume(
            _observation(), evaluated_at=NOW
        )

        assert not result.accepted
        assert "required filling mode is not supported" in result.issues
    finally:
        log.close()


def test_duplicate_observation_is_persisted_once(tmp_path: Path) -> None:
    consumer, log = _consumer(tmp_path)
    try:
        observation = _observation()

        assert consumer.consume(observation, evaluated_at=NOW).accepted
        assert consumer.consume(observation, evaluated_at=NOW).accepted
        assert len(log.research_snapshots()) == 1
    finally:
        log.close()


def test_rejects_incomplete_candle(tmp_path: Path) -> None:
    consumer, log = _consumer(tmp_path)
    try:
        incomplete = _observation()
        payload = incomplete.to_public_payload()
        candles = payload["candles"]
        assert isinstance(candles, dict)
        candles["completed"] = []
        result = consumer.consume(
            ObservationEnvelope.from_payload(payload), evaluated_at=NOW
        )

        assert not result.accepted
        assert "completed M1 candle is missing" in result.issues
    finally:
        log.close()


@pytest.mark.parametrize(
    ("path", "value", "issue"),
    [
        ("instrument.broker_symbol", "USDJPY.a", "unexpected broker symbol"),
        ("instrument.specification.point", 0.0, "invalid broker point or digits"),
        (
            "instrument.specification.supported_filling_modes",
            [],
            "required filling mode is not supported",
        ),
        ("quote.spread_points", 21.0, "invalid or excessive spread"),
    ],
)
def test_rejects_invalid_symbol_metadata(
    tmp_path: Path, path: str, value: object, issue: str
) -> None:
    consumer, log = _consumer(tmp_path)
    try:
        result = consumer.consume(_observation(**{path: value}), evaluated_at=NOW)

        assert not result.accepted
        assert issue in result.issues
    finally:
        log.close()


def test_invalid_timestamp_is_rejected_by_observation_contract() -> None:
    valid = _observation().to_public_payload()
    valid["observed_at_utc"] = "not-a-timestamp"

    with pytest.raises(ValueError, match="observed_at_utc"):
        ObservationEnvelope.from_payload(valid)


def test_preserves_utc_aware_candle_timestamp(tmp_path: Path) -> None:
    consumer, log = _consumer(tmp_path)
    try:
        result = consumer.consume(_observation(), evaluated_at=NOW)

        assert result.snapshot is not None
        timestamp = datetime.fromisoformat(result.snapshot["candle"]["open_time_utc"])
        assert timestamp.tzinfo is not None
        assert timestamp.astimezone(UTC).tzinfo == UTC
    finally:
        log.close()
