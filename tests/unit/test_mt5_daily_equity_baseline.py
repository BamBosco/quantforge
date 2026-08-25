from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from quantforge.config.settings import load_forex_mt5_demo_settings
from quantforge.infrastructure.mt5.daily_equity_baseline import (
    MT5DailyEquityBaselineResolver,
)
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog
from quantforge.infrastructure.mt5.observation_quality import ObservationQualityPolicy
from quantforge.risk.forex_gate import ForexRiskContext, ForexRiskGate

DAY = datetime(2026, 8, 24, tzinfo=UTC)


def _settings():
    return load_forex_mt5_demo_settings(Path("config/forex_mt5_demo_usdjpy.toml"))


def _log(tmp_path: Path) -> SQLiteMarketObservationLog:
    return SQLiteMarketObservationLog(
        tmp_path / "audit.sqlite3",
        quality_policy=ObservationQualityPolicy(max_staleness_seconds=1_000_000_000),
    )


def _observation(
    *,
    observed_at: datetime,
    account_id: str = "123",
    server: str = "Dukascopy-demo-mt5-1",
    equity: float = 10_000.0,
) -> ObservationEnvelope:
    timestamp = observed_at.astimezone(UTC).isoformat()
    return ObservationEnvelope.from_payload(
        {
            "schema_version": 2,
            "observed_at_utc": timestamp,
            "source": {
                "adapter": "mt5_read_only_ea",
                "broker_profile_id": "mt5_runtime_observed",
            },
            "account": {
                "account_id": account_id,
                "server": server,
                "currency": "USD",
                "balance": equity,
                "equity": equity,
                "margin": 0.0,
                "free_margin": equity,
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
                    "supported_filling_modes": ["immediate_or_cancel"],
                },
            },
            "quote": {
                "bid": 159.1,
                "ask": 159.102,
                "tick_time_utc": timestamp,
                "spread_points": 2.0,
            },
            "candles": {"timeframe": "M1", "forming": None, "completed": []},
            "positions": [],
            "active_orders": [],
            "deals": {
                "history_from_utc": timestamp,
                "history_to_utc": timestamp,
                "items": [],
            },
            "terminal": {"connected": True},
            "data_quality": {"adapter_status": "ok", "missing_data": []},
        }
    )


def _snapshot(
    *, observed_at: datetime, account_id: str = "123", equity: float = 9_900.0
) -> dict[str, object]:
    return {
        "observed_at_utc": observed_at.astimezone(UTC).isoformat(),
        "instrument": {"canonical_symbol": "USDJPY", "broker_symbol": "USDJPY"},
        "account": {
            "account_id": account_id,
            "server": "Dukascopy-demo-mt5-1",
            "currency": "USD",
            "equity": equity,
        },
    }


def test_persists_earliest_valid_same_day_baseline(tmp_path: Path) -> None:
    log = _log(tmp_path)
    try:
        earliest = _observation(observed_at=DAY + timedelta(minutes=5), equity=10_000)
        log.append_observation(earliest)
        log.append_observation(
            _observation(observed_at=DAY + timedelta(hours=12), equity=9_900)
        )

        baseline = MT5DailyEquityBaselineResolver(log, _settings()).resolve(
            _snapshot(observed_at=DAY + timedelta(hours=12))
        )

        assert baseline == Decimal("10000.0")
        stored = log.daily_account_equity_baseline(
            account_id="123",
            account_server="Dukascopy-demo-mt5-1",
            broker_symbol="USDJPY",
            baseline_date_utc=DAY.isoformat(),
        )
        assert stored is not None
        assert stored["source_observation_id"] == earliest.observation_id
        assert (
            stored["source_observation_timestamp_utc"]
            == (DAY + timedelta(minutes=5)).isoformat()
        )
    finally:
        log.close()


def test_returns_none_when_no_same_day_baseline_exists(tmp_path: Path) -> None:
    log = _log(tmp_path)
    try:
        baseline = MT5DailyEquityBaselineResolver(log, _settings()).resolve(
            _snapshot(observed_at=DAY + timedelta(hours=12))
        )

        assert baseline is None
    finally:
        log.close()


def test_rejects_baseline_source_from_wrong_day(tmp_path: Path) -> None:
    log = _log(tmp_path)
    try:
        log.append_observation(
            _observation(observed_at=DAY - timedelta(days=1), equity=10_000)
        )

        baseline = MT5DailyEquityBaselineResolver(log, _settings()).resolve(
            _snapshot(observed_at=DAY + timedelta(hours=12))
        )

        assert baseline is None
    finally:
        log.close()


def test_rejects_baseline_source_from_a_different_account(tmp_path: Path) -> None:
    log = _log(tmp_path)
    try:
        log.append_observation(
            _observation(
                observed_at=DAY + timedelta(minutes=5),
                account_id="other",
                equity=10_000,
            )
        )

        baseline = MT5DailyEquityBaselineResolver(log, _settings()).resolve(
            _snapshot(observed_at=DAY + timedelta(hours=12), account_id="123")
        )

        assert baseline is None
    finally:
        log.close()


def test_daily_loss_is_calculated_against_persisted_baseline(tmp_path: Path) -> None:
    log = _log(tmp_path)
    try:
        log.append_observation(
            _observation(observed_at=DAY + timedelta(minutes=5), equity=10_000)
        )
        snapshot = _snapshot(observed_at=DAY + timedelta(hours=12), equity=9_700)
        baseline = MT5DailyEquityBaselineResolver(log, _settings()).resolve(snapshot)
        assert baseline == Decimal("10000.0")
        risk_snapshot = {
            **snapshot,
            "instrument": {
                "canonical_symbol": "USDJPY",
                "specification": {
                    "volume_min": 0.01,
                    "volume_max": 100.0,
                    "volume_step": 0.01,
                    "contract_size": 100_000.0,
                },
            },
            "quote": {"spread_points": 2.0},
            "position_state": {"positions": []},
        }
        decision = ForexRiskGate(_settings().risk).evaluate(
            trade_intent={
                "direction": "BUY",
                "entry_price": 159.1,
                "stop_loss": 159.0,
                "take_profit": 159.3,
                "risk_percent": 0.005,
            },
            market_snapshot=risk_snapshot,
            context=ForexRiskContext(baseline),
        )

        assert decision.status == "rejected"
        assert "maximum daily loss reached" in decision.reasons
    finally:
        log.close()
