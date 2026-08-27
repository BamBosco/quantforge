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


def detect_boundary_gaps(
    observations: list[dict[str, Any]],
    threshold_seconds: float = 90,
    boundary_threshold_seconds: float = 15 * 60,
) -> list[dict[str, Any]]:
    """Classify receipt gaps and retain boundary-adjacent quote evidence."""
    candidates: list[dict[str, Any]] = []
    for earlier, later in zip(observations, observations[1:], strict=False):
        earlier_time = earlier["event_time"]
        later_time = later["event_time"]
        gap_seconds = (later_time - earlier_time).total_seconds()
        if gap_seconds > threshold_seconds:
            weekday_transition = earlier_time.weekday() > later_time.weekday()
            is_boundary_candidate = (
                gap_seconds >= boundary_threshold_seconds or weekday_transition
            )
            if weekday_transition and earlier_time.weekday() == 4:
                boundary_type = "weekly_close_reopen_candidate"
            elif earlier_time.hour in (20, 21, 22) or later_time.hour in (20, 21, 22):
                boundary_type = "daily_break_rollover_candidate"
            else:
                boundary_type = "unclassified_long_gap"
            candidates.append(
                {
                    "before_utc": earlier_time.isoformat(),
                    "after_utc": later_time.isoformat(),
                    "gap_seconds": gap_seconds,
                    "classification": (
                        "boundary_candidate"
                        if is_boundary_candidate
                        else "ordinary_collection_gap"
                    ),
                    "boundary_type": boundary_type,
                    "before_weekday": earlier_time.strftime("%A"),
                    "after_weekday": later_time.strftime("%A"),
                    "before_spread_points": earlier["spread_points"],
                    "after_spread_points": later["spread_points"],
                    "before_server_minus_utc_minutes": earlier["server_offset"],
                    "after_server_minus_utc_minutes": later["server_offset"],
                }
            )
    return candidates


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
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
    observations: list[dict[str, Any]] = []
    spreads: list[float] = []
    for row in accepted:
        payload = json.loads(str(row["payload_json"]))
        event_time = _parse_timestamp(str(row["event_time_utc"]))
        if event_time is None:
            continue
        spread_points = float(payload["quote"]["spread_points"])
        spreads.append(spread_points)
        provenance = payload.get("time_provenance", {})
        server = _parse_terminal_time(provenance.get("terminal_server_time"))
        utc = _parse_timestamp(provenance.get("terminal_utc_time"))
        local = _parse_terminal_time(provenance.get("terminal_local_time"))
        server_offset: int | None = None
        if server and utc:
            offset = round(
                (server - utc.replace(tzinfo=None)).total_seconds() / 60
            )
            offsets[offset] += 1
            server_offset = offset
        if local and utc:
            offset = round(
                (local - utc.replace(tzinfo=None)).total_seconds() / 60
            )
            local_offsets[offset] += 1
        observations.append(
            {
                "event_time": event_time,
                "spread_points": spread_points,
                "server_offset": server_offset,
            }
        )

    boundary_gaps = detect_boundary_gaps(observations)
    return {
        "database": str(database),
        "instrument": instrument,
        "total_receipts": len(rows),
        "database_total_receipts": connection_total(database),
        "accepted_receipts": len(accepted),
        "provenance_receipts": sum(offsets.values()),
        "first_event_utc": (
            observations[0]["event_time"].isoformat() if observations else None
        ),
        "last_event_utc": (
            observations[-1]["event_time"].isoformat() if observations else None
        ),
        "server_minus_utc_minutes": dict(offsets),
        "local_minus_utc_minutes": dict(local_offsets),
        "spread_points": {
            "minimum": min(spreads) if spreads else None,
            "maximum": max(spreads) if spreads else None,
        },
        "observation_gaps_over_90_seconds": len(boundary_gaps),
        "largest_observation_gap_seconds": max(
            (float(gap["gap_seconds"]) for gap in boundary_gaps), default=0
        ),
        "boundary_gap_candidates": boundary_gaps,
        "boundary_gap_classifications": dict(
            Counter(str(gap["classification"]) for gap in boundary_gaps)
        ),
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
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    result = analyze(args.database, args.instrument)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
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
