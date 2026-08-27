"""Unit checks for the authenticated, non-executing MT5 bridge."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread

from quantforge.application.experimental_paper_demo import demo_observation
from quantforge.infrastructure.mt5.read_only_bridge import MT5Snapshot, create_server
from quantforge.infrastructure.mt5.xauusd_broker_profile_audit import (
    SQLiteXAUUSDBrokerProfileAudit,
)


def _payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "observed_at_utc": "2026-08-14T10:00:00Z",
        "account": {
            "login": 5634559,
            "server": "Headway-Demo",
            "currency": "USD",
            "balance": 10_000.0,
            "equity": 9_995.0,
            "margin": 100.0,
            "free_margin": 9_895.0,
        },
        "symbol": {
            "name": "XAUUSD",
            "bid": 4342.67,
            "ask": 4342.98,
            "point": 0.01,
            "digits": 2,
            "volume_min": 0.01,
            "volume_max": 100.0,
            "volume_step": 0.01,
        },
        "position_count": 0,
        "terminal": {"connected": True, "trade_allowed": True},
    }


def _candidate_006_payload(observed_at: datetime) -> dict[str, object]:
    observation = demo_observation(
        observed_at=observed_at,
        bid=Decimal("4645.335"),
        ask=Decimal("4645.835"),
    )
    observation.payload["account"]["server"] = "Dukascopy-demo-mt5-1"
    observation.payload["candles"]["completed"] = [
        {
            "open_time_utc": (observed_at - timedelta(minutes=1)).isoformat(),
            "open": 4633.205,
            "high": 4635.245,
            "low": 4633.205,
            "close": 4634.195,
            "tick_volume": 225,
        }
    ]
    observation.payload["instrument"]["specification"].update(
        {
            "trade_mode": 4,
            "order_mode": 127,
            "stop_level": 0,
            "freeze_level": 0,
            "trade_calculation_mode": 1,
            "profit_currency": "USD",
            "margin_currency": "XAU",
            "tick_size": 0.001,
            "tick_value": 0.1,
            "tick_value_loss": 0.1,
            "tick_value_profit": 0.1,
        }
    )
    observation.payload["terminal"]["trade_allowed"] = True
    return observation.payload


def _post_snapshot(port: int, payload: dict[str, object]) -> int:
    receiver = HTTPConnection("127.0.0.1", port)
    receiver.request(
        "POST",
        "/v1/mt5/snapshots",
        body=json.dumps(payload),
        headers={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        },
    )
    return receiver.getresponse().status


def test_snapshot_contract_accepts_valid_read_only_facts() -> None:
    snapshot = MT5Snapshot.from_payload(_payload())

    assert snapshot.symbol == "XAUUSD"
    assert snapshot.observed_at_utc == datetime(2026, 8, 14, 10, 0, tzinfo=UTC)


def test_snapshot_contract_accepts_mql5_utc_timestamp() -> None:
    payload = _payload()
    payload["observed_at_utc"] = "2026.08.14 10:00:00Z"

    snapshot = MT5Snapshot.from_payload(payload)

    assert snapshot.observed_at_utc == datetime(2026, 8, 14, 10, 0, tzinfo=UTC)


def test_snapshot_contract_rejects_crossed_quote() -> None:
    payload = _payload()
    symbol = payload["symbol"]
    assert isinstance(symbol, dict)
    symbol["ask"] = 4342.00

    try:
        MT5Snapshot.from_payload(payload)
    except ValueError as error:
        assert "bid/ask" in str(error)
    else:
        raise AssertionError("crossed quote must be rejected")


def test_bridge_refuses_a_non_loopback_listener() -> None:
    try:
        create_server("0.0.0.0", 8765, "test-token")
    except ValueError as error:
        assert "loopback" in str(error)
    else:
        raise AssertionError("a non-loopback listener must be rejected")


def test_bridge_has_no_order_endpoint_and_requires_token() -> None:
    server = create_server("127.0.0.1", 0, "test-token")
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        unauthenticated = HTTPConnection("127.0.0.1", port)
        unauthenticated.request(
            "POST", "/v1/mt5/snapshots", body=json.dumps(_payload())
        )
        assert unauthenticated.getresponse().status == 401

        order_request = HTTPConnection("127.0.0.1", port)
        order_request.request(
            "POST",
            "/v1/mt5/orders",
            headers={"Authorization": "Bearer test-token"},
        )
        assert order_request.getresponse().status == 404

        receiver = HTTPConnection("127.0.0.1", port)
        receiver.request(
            "POST",
            "/v1/mt5/snapshots",
            body=json.dumps(_payload()),
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json",
            },
        )
        assert receiver.getresponse().status == 202
    finally:
        server.shutdown()
        server.server_close()


def test_bridge_accepts_complete_v2_read_only_observation(tmp_path: Path) -> None:
    database = tmp_path / "observations.sqlite3"
    server = create_server("127.0.0.1", 0, "test-token", database)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        observation = demo_observation(
            observed_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
            bid=Decimal("99.9"),
            ask=Decimal("100"),
        )
        specification = observation.payload["instrument"]["specification"]
        specification.update(
            {
                "trade_mode": 4,
                "order_mode": 127,
                "stop_level": 0,
                "freeze_level": 0,
                "trade_calculation_mode": 1,
                "profit_currency": "USD",
                "margin_currency": "USD",
                "tick_size": 0.001,
                "tick_value": 0.1,
                "tick_value_loss": 0.1,
                "tick_value_profit": 0.1,
            }
        )
        observation.payload["terminal"]["trade_allowed"] = True
        receiver = HTTPConnection("127.0.0.1", port)
        receiver.request(
            "POST",
            "/v1/mt5/snapshots",
            body=json.dumps(observation.payload),
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json",
            },
        )
        assert receiver.getresponse().status == 202
        latest = HTTPConnection("127.0.0.1", port)
        latest.request(
            "GET",
            "/v1/mt5/latest",
            headers={"Authorization": "Bearer test-token"},
        )
        latest_payload = json.loads(latest.getresponse().read())
        assert latest_payload["schema_version"] == 2
        assert latest_payload["instrument"]["specification"]["profit_currency"] == "USD"
        assert latest_payload["instrument"]["specification"]["tick_value_loss"] == 0.1
        assert latest_payload["terminal"]["trade_allowed"] is True
    finally:
        server.shutdown()
        server.close()


def test_bridge_preserves_terminal_clock_provenance(tmp_path: Path) -> None:
    database = tmp_path / "observations.sqlite3"
    server = create_server("127.0.0.1", 0, "test-token", database)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        observation = demo_observation(
            observed_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
            bid=Decimal("99.9"),
            ask=Decimal("100"),
        )
        observation.payload["time_provenance"] = {
            "terminal_server_time": "2026.08.21 16:00:00",
            "terminal_local_time": "2026.08.21 14:00:00",
            "terminal_utc_time": "2026.08.21 13:00:00Z",
        }
        assert _post_snapshot(server.server_address[1], observation.payload) == 202
        latest = HTTPConnection("127.0.0.1", server.server_address[1])
        latest.request(
            "GET", "/v1/mt5/latest", headers={"Authorization": "Bearer test-token"}
        )
        payload = json.loads(latest.getresponse().read())
        assert (
            payload["time_provenance"]["terminal_server_time"]
            == "2026.08.21 16:00:00"
        )
    finally:
        server.shutdown()
        server.close()


def test_generic_bridge_keeps_eurusd_receipts_in_their_own_log(tmp_path: Path) -> None:
    """EURUSD clock evidence must not require Candidate 006's XAUUSD audit."""
    database = tmp_path / "assexmarkets_eurusd.sqlite3"
    server = create_server("127.0.0.1", 0, "test-token", database)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        observation = demo_observation(
            observed_at=datetime(2026, 8, 27, 4, tzinfo=UTC),
            bid=Decimal("1.17000"),
            ask=Decimal("1.17010"),
        )
        observation.payload["instrument"]["canonical_instrument"] = "EURUSD"
        observation.payload["instrument"]["broker_symbol"] = "EURUSD"
        observation.payload["time_provenance"] = {
            "terminal_server_time": "2026.08.27 07:00:00",
            "terminal_local_time": "2026.08.27 05:00:00",
            "terminal_utc_time": "2026-08-27T04:00:00Z",
        }
        assert _post_snapshot(server.server_address[1], observation.payload) == 202

        latest = HTTPConnection("127.0.0.1", server.server_address[1])
        latest.request(
            "GET", "/v1/mt5/latest", headers={"Authorization": "Bearer test-token"}
        )
        payload = json.loads(latest.getresponse().read())
        assert payload["instrument"]["canonical_instrument"] == "EURUSD"
        assert database.exists()
    finally:
        server.shutdown()
        server.close()


def test_bridge_opt_in_persists_only_fresh_complete_candidate_006_receipts(
    tmp_path: Path,
) -> None:
    observation_database = tmp_path / "observations.sqlite3"
    candidate_audit_database = tmp_path / "candidate_006.sqlite3"
    server = create_server(
        "127.0.0.1",
        0,
        "test-token",
        observation_database,
        candidate_006_audit_path=candidate_audit_database,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    audit = SQLiteXAUUSDBrokerProfileAudit(candidate_audit_database)
    port = server.server_address[1]
    try:
        valid = _candidate_006_payload(datetime.now(UTC))
        assert _post_snapshot(port, valid) == 202
        assert audit.count() == 1

        assert _post_snapshot(port, valid) == 400
        assert audit.count() == 1

        stale = _candidate_006_payload(datetime.now(UTC) - timedelta(minutes=5))
        assert _post_snapshot(port, stale) == 400
        assert audit.count() == 1

        incomplete = _candidate_006_payload(datetime.now(UTC))
        incomplete["instrument"]["specification"].pop("tick_value_loss")
        assert _post_snapshot(port, incomplete) == 400
        assert audit.count() == 1
    finally:
        audit.close()
        server.shutdown()
        server.close()


def test_read_only_ea_reports_native_xauusd_calculation_metadata() -> None:
    source = (
        Path(__file__).parents[2] / "mt5" / "experts" / "QuantForgeReadOnlyBridge.mq5"
    ).read_text()

    for property_name in (
        "SYMBOL_TRADE_MODE",
        "SYMBOL_ORDER_MODE",
        "SYMBOL_TRADE_STOPS_LEVEL",
        "SYMBOL_TRADE_FREEZE_LEVEL",
        "SYMBOL_TRADE_CALC_MODE",
        "SYMBOL_CURRENCY_PROFIT",
        "SYMBOL_CURRENCY_MARGIN",
        "SYMBOL_TRADE_TICK_SIZE",
        "SYMBOL_TRADE_TICK_VALUE",
        "SYMBOL_TRADE_TICK_VALUE_LOSS",
        "SYMBOL_TRADE_TICK_VALUE_PROFIT",
    ):
        assert property_name in source

    assert "time_provenance" in source
    assert "TimeCurrent()" in source
    assert "TimeGMT()" in source
    assert "OrderSend(" not in source
