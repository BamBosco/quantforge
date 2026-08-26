#!/usr/bin/env python3
"""Summarize MT5 time-provenance fields from observation receipts.

This is intentionally read-only and is meant to help review fresh MT5 receipts
before making any timezone or session policy claim. It does not exercise the
broker or place an order.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _parse_terminal_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive path
                raise ValueError(
                    f"invalid JSON on line {line_number} of {path}"
                ) from exc
            if isinstance(record, dict):
                yield record


def _iter_sqlite(path: Path) -> Iterator[dict]:
    connection = sqlite3.connect(str(path))
    try:
        rows = connection.execute(
            "SELECT payload_json FROM observation_event WHERE payload_json IS NOT NULL"
        ).fetchall()
        for (payload_json,) in rows:
            try:
                record = json.loads(payload_json)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive path
                raise ValueError(f"invalid payload JSON in {path}") from exc
            if isinstance(record, dict):
                yield record
    finally:
        connection.close()


def _records_from_path(path: Path) -> Iterable[dict]:
    if path.suffix == ".jsonl":
        return _iter_jsonl(path)
    if path.suffix in {".sqlite3", ".db", ".sqlite"}:
        return _iter_sqlite(path)
    raise ValueError(f"unsupported provenance file type: {path}")


def _payload_for(record: dict) -> dict:
    if isinstance(record.get("payload"), dict):
        return record["payload"]
    return record


def _summarize_record(record: dict) -> dict | None:
    payload = _payload_for(record)
    provenance = payload.get("time_provenance")
    if not isinstance(provenance, dict):
        return None

    observed_at = _parse_iso8601(payload.get("observed_at_utc"))
    if observed_at is None:
        return None

    results: dict[str, object] = {
        "observed_at_utc": payload.get("observed_at_utc"),
        "event_time_utc": (
            record.get("event_time_utc") or payload.get("observed_at_utc")
        ),
    }
    for field_name, key in {
        "terminal_server_time": "terminal_server_time",
        "terminal_local_time": "terminal_local_time",
        "terminal_utc_time": "terminal_utc_time",
    }.items():
        raw = provenance.get(key)
        parsed = (
            _parse_iso8601(raw)
            if key == "terminal_utc_time"
            else _parse_terminal_time(raw)
        )
        if parsed is None:
            results[field_name] = {"raw": raw, "offset_minutes": None}
            continue
        if parsed.tzinfo is not None:
            delta_seconds = (parsed - observed_at).total_seconds()
        else:
            delta_seconds = (
                parsed - observed_at.replace(tzinfo=None)
            ).total_seconds()
        results[field_name] = {
            "raw": raw,
            "offset_minutes": round(delta_seconds / 60.0, 2),
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        help="SQLite observation database or JSONL evidence file to inspect",
    )
    args = parser.parse_args()

    records = list(_records_from_path(args.path))
    provenance_records: list[dict] = []
    for record in records:
        summary = _summarize_record(record)
        if summary is not None:
            provenance_records.append(summary)

    if not provenance_records:
        print(
            "No MT5 time_provenance entries found in "
            f"{args.path} ({len(records)} records scanned)."
        )
        return

    print(f"Found {len(provenance_records)} MT5 time_provenance entries in {args.path}")
    for index, entry in enumerate(provenance_records, start=1):
        print(f"\nEntry {index}")
        print(f"  observed_at_utc: {entry['observed_at_utc']}")
        for label in (
            "terminal_server_time",
            "terminal_local_time",
            "terminal_utc_time",
        ):
            value = entry.get(label)
            if isinstance(value, dict):
                raw = value.get("raw")
                offset = value.get("offset_minutes")
                print(f"  {label}: raw={raw} offset_minutes={offset}")


if __name__ == "__main__":
    main()
