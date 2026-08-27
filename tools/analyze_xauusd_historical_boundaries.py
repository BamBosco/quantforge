#!/usr/bin/env python3
"""Analyze source-clock daily boundaries and long gaps in an XAUUSD M1 export."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def analyze(path: Path) -> dict[str, Any]:
    daily: dict[str, dict[str, Any]] = {}
    previous: tuple[datetime, float] | None = None
    gaps: list[dict[str, Any]] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            timestamp = datetime.strptime(
                f"{row['<DATE>']} {row['<TIME>']}", "%Y.%m.%d %H:%M:%S"
            )
            spread = float(row["<SPREAD>"])
            date_key = timestamp.date().isoformat()
            current = daily.setdefault(
                date_key,
                {
                    "first": timestamp,
                    "last": timestamp,
                    "first_spread": spread,
                    "last_spread": spread,
                },
            )
            current["last"] = timestamp
            current["last_spread"] = spread
            if previous is not None:
                gap_seconds = (timestamp - previous[0]).total_seconds()
                if gap_seconds > 30 * 60:
                    gaps.append(
                        {
                            "before": previous[0].isoformat(),
                            "after": timestamp.isoformat(),
                            "gap_seconds": gap_seconds,
                            "before_spread": previous[1],
                            "after_spread": spread,
                        }
                    )
            previous = (timestamp, spread)

    first_hours = Counter(item["first"].hour for item in daily.values())
    last_hours = Counter(item["last"].hour for item in daily.values())
    delayed_opens = [
        {
            "date": date_key,
            "weekday": datetime.fromisoformat(date_key).strftime("%A"),
            "first": item["first"].strftime("%H:%M"),
            "last": item["last"].strftime("%H:%M"),
            "first_spread": item["first_spread"],
            "last_spread": item["last_spread"],
        }
        for date_key, item in daily.items()
        if item["first"].hour != 1
    ]
    early_closes = [
        {
            "date": date_key,
            "weekday": datetime.fromisoformat(date_key).strftime("%A"),
            "first": item["first"].strftime("%H:%M"),
            "last": item["last"].strftime("%H:%M"),
            "first_spread": item["first_spread"],
            "last_spread": item["last_spread"],
        }
        for date_key, item in daily.items()
        if item["last"].hour * 60 + item["last"].minute < 23 * 60 + 30
    ]
    return {
        "dataset": str(path),
        "observed_dates": len(daily),
        "first_bar_hours": dict(sorted(first_hours.items())),
        "last_bar_hours": dict(sorted(last_hours.items())),
        "delayed_or_shifted_opens": delayed_opens,
        "early_close_candidates": early_closes,
        "gaps_over_30_minutes": gaps,
        "long_gap_count": len(gaps),
        "largest_gap_seconds": max(
            (gap["gap_seconds"] for gap in gaps), default=0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.dataset)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
