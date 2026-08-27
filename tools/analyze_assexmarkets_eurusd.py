#!/usr/bin/env python3
"""Analyze isolated AssexMarkets EURUSD MT5 clock and schedule observations."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def analyze(database: Path, instrument: str = "EURUSD") -> dict[str, Any]:
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT event_time_utc, payload_json, quality_status, broker_symbol "
            "FROM observation_event WHERE broker_symbol = ? ORDER BY id",
            (instrument,),
        ).fetchall()
    finally:
        connection.close()

    accepted = [row for row in rows if row["quality_status"] == "accepted"]
    offsets: Counter[int] = Counter()
    local_offsets: Counter[int] = Counter()
    event_times: list[datetime] = []
    spreads: list[float] = []
    for row in accepted:
        payload = json.loads(str(row["payload_json"]))
        event_times.append(_parse_timestamp(str(row["event_time_utc"])))
        spreads.append(float(payload["quote"]["spread_points"]))
        provenance = payload.get("time_provenance", {})
        server = _parse_terminal_time(provenance.get("terminal_server_time"))
        utc = _parse_timestamp(str(provenance.get("terminal_utc_time")))
        local = _parse_terminal_time(provenance.get("terminal_local_time"))
        if server and utc:
            offset = round(
                (server - utc.replace(tzinfo=None)).total_seconds() / 60
            )
            offsets[offset] += 1
        if local and utc:
            offset = round(
                (local - utc.replace(tzinfo=None)).total_seconds() / 60
            )
            local_offsets[offset] += 1

    gaps = [
        (later - earlier).total_seconds()
        for earlier, later in zip(event_times, event_times[1:], strict=False)
        if (later - earlier).total_seconds() > 90
    ]
    return {
        "database": str(database),
        "instrument": instrument,
        "total_receipts": len(rows),
        "database_total_receipts": connection_total(database),
        "accepted_receipts": len(accepted),
        "provenance_receipts": sum(offsets.values()),
        "first_event_utc": event_times[0].isoformat() if event_times else None,
        "last_event_utc": event_times[-1].isoformat() if event_times else None,
        "server_minus_utc_minutes": dict(offsets),
        "local_minus_utc_minutes": dict(local_offsets),
        "spread_points": {
            "minimum": min(spreads) if spreads else None,
            "maximum": max(spreads) if spreads else None,
        },
        "observation_gaps_over_90_seconds": len(gaps),
        "largest_observation_gap_seconds": max(gaps, default=0),
        "schedule_coverage": {
            "weekly_open_close": "not_observed",
            "daily_break": "not_observed",
            "rollover": "not_observed",
            "dst_boundary": "not_observed",
        },
    }


def connection_total(database: Path) -> int:
    connection = sqlite3.connect(str(database))
    try:
        return int(
            connection.execute("SELECT count(*) FROM observation_event").fetchone()[0]
        )
    finally:
        connection.close()


def _parse_terminal_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--instrument", default="EURUSD")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    result = analyze(args.database, args.instrument)
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    print(
        f"{result['instrument']} accepted receipts: "
        f"{result['accepted_receipts']} "
        f"(database total: {result['database_total_receipts']})"
    )
    print(f"Coverage: {result['first_event_utc']} through {result['last_event_utc']}")
    print(f"Server-minus-UTC minutes: {result['server_minus_utc_minutes']}")
    print(f"Local-minus-UTC minutes: {result['local_minus_utc_minutes']}")
    print(f"Spread points: {result['spread_points']}")
    print("Weekly/daily break/rollover/DST coverage: not observed")


if __name__ == "__main__":
    main()
