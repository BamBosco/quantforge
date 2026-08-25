"""Deterministic, research-only result reporting for Candidate 003."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from quantforge.backtest.candidate_003 import (
    CANDIDATE_ID,
    CANDIDATE_VERSION,
    EVALUATION_SHA256,
    Candidate003Run,
)
from quantforge.backtest.replay import ReplaySessionResult, SessionOutcome
from quantforge.backtest.validation import (
    PerformanceMetrics,
    ValidationSession,
    evaluate_performance,
)


def build_research_report(run: Candidate003Run) -> dict[str, Any]:
    """Serialize an existing run without replaying, changing rules, or trading."""
    scenarios: dict[str, dict[str, Any]] = {}
    for name, results in run.scenarios.items():
        validation = run.validation
        split = validation.splits[name]
        windows = validation.walk_forward[name]
        outcome_counts = Counter(result.outcome.value for result in results)
        scenarios[name] = {
            "additional_slippage_points": name,
            "total_replayed_weekday_outcomes": len(results),
            "structurally_qualifying_sessions": sum(
                result.outcome is not SessionOutcome.INVALID_DATA for result in results
            ),
            "outcome_counts": {
                outcome.value: outcome_counts.get(outcome.value, 0)
                for outcome in SessionOutcome
            },
            "session_journal": [_session_result(result) for result in results],
            "full_sample": _metrics(validation.full_sample_cost_stress.scenarios[name]),
            "development": _metrics(validation.development_cost_stress.scenarios[name]),
            "holdout": _metrics(evaluate_performance(split.holdout)),
            "walk_forward": [
                {
                    "window_number": index,
                    "training": _window_metrics(window.training),
                    "validation": _window_metrics(window.validation),
                }
                for index, window in enumerate(windows, start=1)
            ],
        }
    return {
        "report_type": "candidate_003_deterministic_evaluation_research_result",
        "research_only": True,
        "execution_authority": "no_paper_mt5_broker_or_live_approval",
        "candidate": {
            "id": CANDIDATE_ID,
            "version": CANDIDATE_VERSION,
        },
        "evaluation_dataset_sha256": EVALUATION_SHA256,
        "scenarios": scenarios,
        "exclusions": [
            {
                "session_day": exclusion.session_day.isoformat(),
                "reason": exclusion.reason,
            }
            for exclusion in run.exclusions
        ],
        "research_gate": {
            "passed": run.validation.gate_decision.passed,
            "reasons": list(run.validation.gate_decision.reasons),
        },
    }


def write_research_report(run: Candidate003Run, path: Path) -> dict[str, Any]:
    """Write exactly one stable JSON rendering of an already-completed run."""
    report = build_research_report(run)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=_json_value) + "\n",
        encoding="utf-8",
    )
    return report


def concise_summary(report: dict[str, Any]) -> str:
    """Return a terminal-safe summary that does not relabel replayed sessions."""
    scenario_zero = report["scenarios"]["0"]
    gate = report["research_gate"]
    replayed = scenario_zero["total_replayed_weekday_outcomes"]
    qualifying = scenario_zero["structurally_qualifying_sessions"]
    return (
        "Candidate 003 deterministic evaluation replay complete: "
        f"{replayed} replayed weekday outcomes; "
        f"{qualifying} structurally qualifying "
        f"sessions; research gate {'PASS' if gate['passed'] else 'FAIL'}"
    )


def _metrics(metrics: PerformanceMetrics) -> dict[str, Any]:
    return {
        "sessions": metrics.sessions,
        "completed_trades": metrics.completed_trades,
        "wins": metrics.wins,
        "losses": metrics.losses,
        "total_r": metrics.total_r,
        "mean_r": metrics.mean_r,
        "maximum_drawdown_r": metrics.maximum_drawdown_r,
        "profit_factor": metrics.profit_factor,
    }


def _session_result(result: ReplaySessionResult) -> dict[str, Any]:
    return {
        "session_day": result.session_day.isoformat(),
        "outcome": result.outcome.value,
        "entry_side": result.entry_side,
        "entry_price": result.entry_price,
        "exit_price": result.exit_price,
        "r_multiple": result.r_multiple,
        "events": [
            {
                "timestamp": event.timestamp.isoformat(),
                "kind": event.kind.value,
                "detail": event.detail,
                "price": event.price,
            }
            for event in result.events
        ],
    }


def _window_metrics(sessions: Sequence[ValidationSession]) -> dict[str, Any]:
    metrics = _metrics(evaluate_performance(sessions))
    metrics["start_session"] = sessions[0].session_day
    metrics["end_session"] = sessions[-1].session_day
    return metrics


def _json_value(value: object) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"not JSON serializable: {type(value)!r}")
