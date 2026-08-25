#!/usr/bin/env python3
"""Stream structural checks for a frozen MT5 M1 export; never run a strategy."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

REQUIRED_COLUMNS = {
    "<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>",
    "<TICKVOL>", "<SPREAD>",
}
WINDOW_START = time(8, 20)
WINDOW_END = time(13, 30)
WINDOW_MINUTES = 311


def parse_timestamp(row: dict[str, str], source_timezone: ZoneInfo) -> datetime:
    value = f"{row['<DATE>'].strip()} {row['<TIME>'].strip()}"
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=source_timezone).astimezone(timezone.utc)
        except ValueError:
            pass
    raise ValueError("unsupported timestamp")


def inspect(path: Path, source_timezone: ZoneInfo) -> dict[str, object]:
    counts: dict[str, int] = defaultdict(int)
    session_minutes: dict[date, set[datetime]] = defaultdict(set)
    session_duplicate: set[date] = set()
    first: datetime | None = None
    last: datetime | None = None
    previous: datetime | None = None
    descending = 0
    ascending = 0

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError("unsupported MT5 M1 schema")
        for line, row in enumerate(reader, 2):
            counts["rows"] += 1
            try:
                timestamp = parse_timestamp(row, source_timezone)
                values = [Decimal(row[field].strip()) for field in ("<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>")]
                tick_volume = int(row["<TICKVOL>"].strip())
                spread = int(row["<SPREAD>"].strip())
            except (KeyError, ValueError, InvalidOperation):
                counts["malformed_rows"] += 1
                continue
            open_, high, low, close = values
            if min(values) <= 0:
                counts["non_positive_prices"] += 1
            if low > min(open_, close, high) or high < max(open_, close, low):
                counts["invalid_ohlc"] += 1
            if tick_volume == 0:
                counts["zero_tick_volume"] += 1
            if spread < 0:
                counts["negative_spread"] += 1
            if previous is not None:
                descending += timestamp < previous
                ascending += timestamp > previous
            previous = timestamp
            first = timestamp if first is None else min(first, timestamp)
            last = timestamp if last is None else max(last, timestamp)
            new_york = timestamp.astimezone(ZoneInfo("America/New_York"))
            if new_york.weekday() < 5 and WINDOW_START <= new_york.time() <= WINDOW_END:
                existing = session_minutes[new_york.date()]
                if timestamp in existing:
                    session_duplicate.add(new_york.date())
                existing.add(timestamp)

    if first is None or last is None:
        raise ValueError("export contains no valid rows")
    session_day = first.astimezone(ZoneInfo("America/New_York")).date()
    final_day = last.astimezone(ZoneInfo("America/New_York")).date()
    required_days: list[date] = []
    while session_day <= final_day:
        if session_day.weekday() < 5:
            required_days.append(session_day)
        session_day += timedelta(days=1)
    incomplete = [
        day for day in required_days
        if len(session_minutes[day]) != WINDOW_MINUTES or day in session_duplicate
    ]
    counts["required_weekdays"] = len(required_days)
    counts["complete_sessions"] = len(required_days) - len(incomplete)
    counts["incomplete_sessions"] = len(incomplete)
    counts["required_window_duplicates"] = len(session_duplicate)
    counts["descending_transitions"] = descending
    counts["ascending_transitions"] = ascending
    return {
        "counts": dict(counts),
        "first": first,
        "last": last,
        "incomplete": incomplete,
    }


def render(name: str, result: dict[str, object]) -> str:
    counts = result["counts"]
    assert isinstance(counts, dict)
    incomplete = result["incomplete"]
    assert isinstance(incomplete, list)
    dates = ", ".join(day.isoformat() for day in incomplete) or "none"
    return "\n".join((
        f"## {name}",
        "",
        f"- Valid rows: {counts.get('rows', 0)}",
        f"- Actual UTC coverage: {result['first'].isoformat()} through {result['last'].isoformat()}",
        f"- Malformed rows: {counts.get('malformed_rows', 0)}",
        f"- Invalid OHLC: {counts.get('invalid_ohlc', 0)}",
        f"- Non-positive prices: {counts.get('non_positive_prices', 0)}",
        f"- Negative spreads: {counts.get('negative_spread', 0)}",
        f"- Zero tick-volume rows: {counts.get('zero_tick_volume', 0)}",
        f"- Required New York weekdays: {counts.get('required_weekdays', 0)}",
        f"- Complete 08:20–13:30 sessions: {counts.get('complete_sessions', 0)}",
        f"- Incomplete required sessions: {counts.get('incomplete_sessions', 0)}",
        f"- Duplicate timestamps in required windows: {counts.get('required_window_duplicates', 0)}",
        f"- Incomplete dates: {dates}",
        "",
    ))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--confirmation", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result_evaluation = inspect(args.evaluation, ZoneInfo("UTC"))
    result_confirmation = inspect(args.confirmation, ZoneInfo("UTC"))
    report = "\n".join((
        "# Exness XAUUSDm M1 Structural Quality Check — Candidate 002",
        "",
        "This check validates only frozen-file structure and required-session continuity. It does not calculate a signal, simulate execution, or run a replay.",
        "",
        render("Evaluation dataset", result_evaluation),
        render("Confirmation dataset", result_confirmation),
    ))
    args.report.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
