"""Read-only observation-log to PAPER MODE runner integration tests."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from quantforge.application.experimental_paper_demo import demo_observation
from quantforge.application.experimental_paper_runner import build_host, run_once
from quantforge.infrastructure.mt5.observation_log import SQLiteMarketObservationLog


def test_read_only_observation_reaches_paper_runtime(tmp_path: Path) -> None:
    observation_path = tmp_path / "observations.sqlite3"
    source_log = SQLiteMarketObservationLog(observation_path)
    observed_at = datetime(2026, 8, 21, 13, tzinfo=UTC)
    source_log.append_observation(
        demo_observation(
            observed_at=observed_at, bid=Decimal("99.9"), ask=Decimal("100")
        )
    )
    host, runner_log, journal = build_host(
        observation_log_path=observation_path,
        journal_path=tmp_path / "paper.sqlite3",
        kill_switch_path=tmp_path / "KILL_SWITCH",
    )
    try:
        assert run_once(host, runner_log, set(), evaluated_at=observed_at) == 1
        assert [event["event_type"] for event in journal.events()][-1] == (
            "ExecutionOutcomeRecorded"
        )
    finally:
        source_log.close()
        runner_log.close()
        journal.close()


def test_delayed_poll_preserves_the_09_new_york_event_cycle(tmp_path: Path) -> None:
    observation_path = tmp_path / "observations.sqlite3"
    source_log = SQLiteMarketObservationLog(observation_path)
    observed_at = datetime(2026, 8, 21, 13, 0, 45, tzinfo=UTC)
    source_log.append_observation(
        demo_observation(
            observed_at=observed_at, bid=Decimal("99.9"), ask=Decimal("100")
        )
    )
    host, runner_log, journal = build_host(
        observation_log_path=observation_path,
        journal_path=tmp_path / "paper.sqlite3",
        kill_switch_path=tmp_path / "KILL_SWITCH",
    )
    try:
        assert run_once(
            host,
            runner_log,
            set(),
            evaluated_at=datetime(2026, 8, 21, 13, 1, 5, tzinfo=UTC),
        ) == 1
        assert [event["event_type"] for event in journal.events()][-1] == (
            "ExecutionOutcomeRecorded"
        )
    finally:
        source_log.close()
        runner_log.close()
        journal.close()
