from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from quantforge.config.settings import load_forex_mt5_demo_settings
from quantforge.infrastructure.mt5.demo_position_state import (
    MT5DemoPositionStateObserver,
)
from quantforge.infrastructure.mt5.observation_contracts import ObservationEnvelope
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog

NOW = datetime(2026, 8, 24, 21, 30, tzinfo=UTC)


def _observation(
    *, server: str = "Dukascopy-demo-mt5-1", symbol: str = "USDJPY"
) -> ObservationEnvelope:
    timestamp = NOW.isoformat()
    return ObservationEnvelope.from_payload(
        {
            "schema_version": 2,
            "observed_at_utc": timestamp,
            "source": {
                "adapter": "mt5_read_only_ea",
                "broker_profile_id": "mt5_runtime_observed",
            },
            "account": {
                "account_id": "123",
                "server": server,
                "currency": "USD",
                "balance": 10_000.0,
                "equity": 9_998.0,
                "margin": 100.0,
                "free_margin": 9_898.0,
            },
            "instrument": {
                "canonical_instrument": symbol,
                "broker_symbol": symbol,
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
                "bid": 159.080,
                "ask": 159.082,
                "tick_time_utc": timestamp,
                "spread_points": 2.0,
            },
            "candles": {"timeframe": "M1", "forming": None, "completed": []},
            "positions": [
                {
                    "ticket": "1001",
                    "symbol": "USDJPY",
                    "side": "buy",
                    "volume": 0.02,
                    "price_open": 159.000,
                    "price_current": 159.080,
                    "sl": 158.900,
                    "tp": 159.200,
                    "profit": 10.06,
                    "opened_at_utc": "2026-08-24T21:00:00+00:00",
                },
                {
                    "ticket": "1002",
                    "symbol": "EURUSD",
                    "side": "sell",
                    "volume": 0.01,
                    "price_open": 1.1,
                    "price_current": 1.09,
                    "sl": 1.11,
                    "tp": 1.08,
                    "profit": 1.0,
                    "opened_at_utc": "2026-08-24T21:01:00+00:00",
                },
            ],
            "active_orders": [
                {
                    "ticket": "2001",
                    "symbol": "USDJPY",
                    "side": "sell",
                    "type": "sell_limit",
                    "volume": 0.03,
                    "price": 159.200,
                    "sl": 159.300,
                    "tp": 159.000,
                }
            ],
            "deals": {
                "history_from_utc": timestamp,
                "history_to_utc": timestamp,
                "items": [],
            },
            "terminal": {"connected": True},
            "data_quality": {"adapter_status": "ok", "missing_data": []},
        }
    )


def _settings():
    return load_forex_mt5_demo_settings(Path("config/forex_mt5_demo_usdjpy.toml"))


def test_persists_read_only_usdjpy_demo_position_state(tmp_path: Path) -> None:
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    try:
        observation = _observation()
        result = MT5DemoPositionStateObserver(log, _settings()).observe(observation)

        assert result.accepted
        assert result.state is not None
        assert result.state["account"]["balance"] == 10_000.0
        assert result.state["account"]["equity"] == 9_998.0
        assert result.state["open_positions"] == [
            {
                "ticket": "1001",
                "symbol": "USDJPY",
                "direction": "buy",
                "volume": 0.02,
                "entry_price": 159.0,
                "current_price": 159.08,
                "stop_loss": 158.9,
                "take_profit": 159.2,
                "profit": 10.06,
                "opened_at_utc": "2026-08-24T21:00:00+00:00",
            }
        ]
        assert result.state["pending_orders"][0]["order_type"] == "sell_limit"
        stored = log.demo_position_state_observations()
        assert stored[0]["validation_status"] == "accepted"
        assert stored[0]["state"] == result.state
    finally:
        log.close()


def test_rejects_non_demo_or_non_usdjpy_scope_and_persists_reason(
    tmp_path: Path,
) -> None:
    log = SQLiteMarketObservationLog(tmp_path / "audit.sqlite3")
    try:
        result = MT5DemoPositionStateObserver(log, _settings()).observe(
            _observation(server="Dukascopy-live", symbol="EURUSD")
        )

        assert not result.accepted
        assert "unexpected canonical instrument" in result.issues
        assert "unexpected broker symbol" in result.issues
        assert "MT5 account server is not identified as demo" in result.issues
        stored = log.demo_position_state_observations()
        assert stored[0]["validation_status"] == "rejected"
    finally:
        log.close()
