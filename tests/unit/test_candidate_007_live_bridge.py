"""Unit and integration tests for Candidate 007 Live MT5 Observation Bridge."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from http import HTTPStatus
from pathlib import Path
from urllib.request import HTTPError, Request, urlopen
from zoneinfo import ZoneInfo

from quantforge.infrastructure.mt5.candidate_007_live_service import (
    create_candidate_007_live_bridge,
)

NEW_YORK = ZoneInfo("America/New_York")


def make_test_payload(
    observed_at: datetime,
    bid: float = 2400.0,
    ask: float = 2400.20,
    open_bar: float = 2399.0,
    high_bar: float = 2401.0,
    low_bar: float = 2398.5,
    close_bar: float = 2400.0,
) -> dict[str, object]:
    iso_time = observed_at.astimezone(UTC).isoformat()
    mt5_clock = observed_at.strftime("%Y.%m.%d %H:%M:%S")
    return {
        "schema_version": 2,
        "observed_at_utc": iso_time,
        "time_provenance": {
            "terminal_server_time": mt5_clock,
            "terminal_local_time": mt5_clock,
            "terminal_utc_time": iso_time,
        },
        "source": {
            "adapter": "mt5_read_only_ea",
            "broker_profile_id": "mt5_test_broker",
        },
        "account": {
            "account_id": "999999",
            "server": "Demo-Test",
            "currency": "USD",
            "balance": 10000.0,
            "equity": 10000.0,
            "margin": 0.0,
            "free_margin": 10000.0,
        },
        "instrument": {
            "canonical_instrument": "XAUUSD",
            "broker_symbol": "XAUUSD",
            "specification": {
                "point": 0.01,
                "digits": 2,
                "volume_min": 0.01,
                "volume_max": 100.0,
                "volume_step": 0.01,
                "contract_size": 100.0,
            },
        },
        "quote": {
            "bid": bid,
            "ask": ask,
            "tick_time_utc": iso_time,
            "spread_points": (ask - bid) / 0.01,
        },
        "candles": {
            "timeframe": "M1",
            "forming": None,
            "completed": [
                {
                    "open_time_utc": iso_time,
                    "open": open_bar,
                    "high": high_bar,
                    "low": low_bar,
                    "close": close_bar,
                    "tick_volume": 10,
                }
            ],
        },
        "positions": [],
        "active_orders": [],
        "deals": {
            "history_from_utc": iso_time,
            "history_to_utc": iso_time,
            "items": [],
        },
        "terminal": {"connected": True, "trade_allowed": True},
        "data_quality": {"adapter_status": "ok", "missing_data": []},
    }


def test_candidate_007_live_bridge_server(tmp_path: Path) -> None:
    token = "secret-test-token-xyz"
    journal_path = tmp_path / "paper_journal.sqlite3"
    obs_log_path = tmp_path / "mt5_obs.sqlite3"

    server, strategy, portfolio, journal, execution_queue = create_candidate_007_live_bridge(
        host="127.0.0.1",
        port=0,  # OS assigned ephemeral port
        token=token,
        journal_path=journal_path,
        obs_log_path=obs_log_path,
        initial_balance=Decimal("10000"),
    )

    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/v1/mt5/snapshots"
    health_url = f"http://127.0.0.1:{port}/healthz"

    try:
        import threading
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

        # 1. Health check
        with urlopen(health_url, timeout=3) as resp:
            assert resp.status == HTTPStatus.OK

        # 2. Unauthorized request rejection
        bad_req = Request(url, data=b"{}", method="POST")
        try:
            urlopen(bad_req, timeout=3)
            assert False, "Should have been rejected"
        except HTTPError as e:
            assert e.code == HTTPStatus.UNAUTHORIZED

        # 3. Authorized snapshot push
        now = datetime(2026, 8, 28, 9, 30, tzinfo=NEW_YORK)
        payload = make_test_payload(now)
        data = json.dumps(payload).encode("utf-8")

        auth_req = Request(url, data=data, method="POST")
        auth_req.add_header("Content-Type", "application/json")
        auth_req.add_header("Authorization", f"Bearer {token}")

        with urlopen(auth_req, timeout=3) as resp:
            assert resp.status == HTTPStatus.ACCEPTED
            body = json.loads(resp.read().decode("utf-8"))
            assert body["accepted"] is True

        assert obs_log_path.exists()
        assert journal_path.exists()

    finally:
        server.close()
