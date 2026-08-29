from pathlib import Path
from textwrap import dedent

import pytest

from quantforge.market_data import inspect_mt5_bar_evidence


def write_export(path: Path, rows: str) -> None:
    path.write_text(
        dedent(
            """\
            <DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>
            """
        )
        + rows,
        encoding="utf-8",
    )


def test_inspects_timezone_neutral_mt5_bar_evidence(tmp_path: Path) -> None:
    export = tmp_path / "xauusd.csv"
    write_export(
        export,
        "2026.08.14\t01:00:00\t4340\t4341\t4339\t4340.5\t52\t0\t10\n"
        "2026.08.14\t01:01:00\t4340.5\t4342\t4340\t4341\t51\t0\t30\n"
        "2026.08.15\t01:00:00\t4341\t4343\t4340\t4342\t50\t0\t20\n",
    )

    evidence = inspect_mt5_bar_evidence(export)

    assert evidence.row_count == 3
    assert evidence.start_terminal_time.isoformat() == "2026-08-14T01:00:00"
    assert evidence.end_terminal_time.isoformat() == "2026-08-15T01:00:00"
    assert evidence.spread_percentiles == (
        (1, 10),
        (5, 10),
        (50, 20),
        (90, 30),
        (95, 30),
        (99, 30),
        (100, 30),
    )
    assert evidence.complete_session_row_count == 2
    assert evidence.incomplete_terminal_dates == ("2026-08-15",)


def test_rejects_duplicate_timestamp(tmp_path: Path) -> None:
    export = tmp_path / "duplicate.csv"
    write_export(
        export,
        "2026.08.14\t01:00:00\t4340\t4341\t4339\t4340\t52\t0\t10\n"
        "2026.08.14\t01:00:00\t4340\t4341\t4339\t4340\t52\t0\t10\n",
    )

    with pytest.raises(ValueError, match="duplicate"):
        inspect_mt5_bar_evidence(export)
