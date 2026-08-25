from datetime import date, timedelta
from decimal import Decimal

from quantforge.backtest.candidate_003 import Candidate003Run
from quantforge.backtest.candidate_003_report import (
    build_research_report,
    concise_summary,
    write_research_report,
)
from quantforge.backtest.replay import (
    ReplaySessionResult,
    SessionOutcome,
    SkippedSession,
)
from quantforge.backtest.validation import (
    ResearchGate,
    ValidationSession,
    run_research_validation,
)


def _run() -> Candidate003Run:
    start = date(2024, 1, 1)
    results = tuple(
        ReplaySessionResult(
            session_day=start + timedelta(days=index),
            outcome=(
                SessionOutcome.INVALID_DATA
                if index % 10 == 0
                else SessionOutcome.FORCED_EXIT
            ),
            events=(),
            r_multiple=None if index % 10 == 0 else Decimal("1"),
        )
        for index in range(800)
    )
    validation_sessions = tuple(
        ValidationSession(item.session_day, item.r_multiple) for item in results
    )
    validation = run_research_validation(
        {name: validation_sessions for name in ("0", "1", "3")},
        holdout_fraction=Decimal("0.20"),
        training_sessions=252,
        validation_sessions=63,
        step_sessions=63,
        maximum_walk_forward_windows=5,
        gate=ResearchGate(
            minimum_completed_trades=10_000,
            require_positive_total_r=True,
            require_positive_mean_r=True,
            require_positive_holdout=True,
            minimum_positive_walk_forward_windows=2,
        ),
    )
    return Candidate003Run(
        scenarios={name: results for name in ("0", "1", "3")},
        exclusions=(
            SkippedSession(start - timedelta(days=1), "dataset quality exclusion"),
        ),
        validation=validation,
    )


def test_report_serializes_all_frozen_scenarios_and_validation(tmp_path) -> None:
    report = build_research_report(_run())

    assert report["candidate"]["version"] == "0.2-frozen"
    assert len(report["evaluation_dataset_sha256"]) == 64
    assert report["exclusions"] == [
        {"session_day": "2023-12-31", "reason": "dataset quality exclusion"}
    ]
    assert report["research_gate"]["passed"] is False
    assert len(report["research_gate"]["reasons"]) == 3
    for scenario in ("0", "1", "3"):
        result = report["scenarios"][scenario]
        assert result["total_replayed_weekday_outcomes"] == 800
        assert result["structurally_qualifying_sessions"] == 720
        assert result["full_sample"]["completed_trades"] == 720
        assert result["full_sample"]["total_r"] == Decimal("720")
        assert result["holdout"]["completed_trades"] == 144
        assert len(result["walk_forward"]) == 5
        assert result["outcome_counts"]["invalid_data"] == 80
        assert result["outcome_counts"]["forced_exit"] == 720
        assert len(result["session_journal"]) == 800
        assert result["session_journal"][0]["outcome"] == "invalid_data"
        assert result["session_journal"][1]["r_multiple"] == Decimal("1")

    output = tmp_path / "result.json"
    first = write_research_report(_run(), output)
    first_bytes = output.read_bytes()
    second = write_research_report(_run(), output)
    assert first == second
    assert output.read_bytes() == first_bytes
    assert "800 replayed weekday outcomes" in concise_summary(report)
    assert "720 structurally qualifying sessions" in concise_summary(report)
