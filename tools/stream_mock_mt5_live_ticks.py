#!/usr/bin/env python3
"""Stream realistic MT5 EA snapshots into QuantForge Live Bridge."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from quantforge.market_data.mt5_csv import load_mt5_minute_bars

NEW_YORK = ZoneInfo("America/New_York")


def make_ea_snapshot_json(
    *,
    timestamp_utc: datetime,
    bid: float,
    ask: float,
    open_bar: float,
    high_bar: float,
    low_bar: float,
    close_bar: float,
    volume: int = 25,
) -> dict[str, object]:
    """Create an authentic MQL5 QuantForgeReadOnlyBridge JSON snapshot."""
    iso_time = timestamp_utc.astimezone(UTC).isoformat()
    mt5_clock = timestamp_utc.strftime("%Y.%m.%d %H:%M:%S")
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
            "broker_profile_id": "mt5_live_demo",
        },
        "account": {
            "account_id": "12345678",
            "server": "Demo-Server-01",
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
                "supported_filling_modes": ["ioc", "fok"],
                "trade_mode": 0,
                "order_mode": 0,
                "stop_level": 0,
                "freeze_level": 0,
                "trade_calculation_mode": 0,
                "profit_currency": "USD",
                "margin_currency": "USD",
                "tick_size": 0.01,
                "tick_value": 1.0,
                "tick_value_loss": 1.0,
                "tick_value_profit": 1.0,
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
                    "tick_volume": volume,
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream simulated MT5 EA snapshots")
    parser.add_argument("--url", default="http://127.0.0.1:8765/v1/mt5/snapshots")
    parser.add_argument("--token", required=True, help="Bearer token for live bridge")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/candidate_006_second_broker/raw/XAUUSD_M1_202601020100_202608141159.csv"),
    )
    parser.add_argument("--limit-bars", type=int, default=100)
    parser.add_argument("--interval", type=float, default=0.005, help="Seconds between ticks")
    args = parser.parse_args()

    bars = load_mt5_minute_bars(args.data, source_timezone="Etc/UTC")
    stream_bars = bars[: args.limit_bars]

    print(f"Streaming {len(stream_bars)} live MT5 EA snapshots to {args.url}...")

    for i, bar in enumerate(stream_bars, 1):
        spread = 0.20
        bid = float(bar.close)
        ask = bid + spread
        payload = make_ea_snapshot_json(
            timestamp_utc=bar.timestamp,
            bid=bid,
            ask=ask,
            open_bar=float(bar.open),
            high_bar=float(bar.high),
            low_bar=float(bar.low),
            close_bar=float(bar.close),
            volume=bar.tick_volume,
        )

        data = json.dumps(payload).encode("utf-8")
        req = Request(args.url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {args.token}")

        try:
            with urlopen(req, timeout=5) as resp:
                if i % 100 == 0 or i == len(stream_bars):
                    print(f"  Sent {i}/{len(stream_bars)} snapshots (HTTP {resp.status})")
        except Exception as e:
            print(f"Failed sending snapshot {i}: {e}")
            break

        if args.interval > 0:
            time.sleep(args.interval)

    print("Stream finished successfully.")


if __name__ == "__main__":
    main()
