"""Sealed, research-only replay contract for Candidate 003 v0.2.

This module has no broker, MT5, paper-execution, or confirmation-data imports.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from quantforge.backtest.intraday_momentum import (
    IntradayMomentumSettings,
    simulate_intraday_momentum_session,
)
from quantforge.backtest.intraday_momentum_runner import run_intraday_momentum_backtest
from quantforge.backtest.models import MinuteBar
from quantforge.backtest.replay import ReplaySessionResult, SkippedSession
from quantforge.backtest.validation import (
    ResearchValidationReport,
    ValidationSession,
    run_research_validation,
)
from quantforge.config.research_validation import load_research_validation_settings
from quantforge.market_data.mt5_csv import load_mt5_minute_bars

CANDIDATE_ID = "crabel_early_session_directional_breakout_candidate_003"
CANDIDATE_VERSION = "0.2-frozen"
EVALUATION_FILENAME = "XAUUSD_M1_201908010105_202308012354.csv"
EVALUATION_SHA256 = "7942acbdafb1343a8d42032d8048a6f43ecc9b7e8df03fab40908b18dc3635ef"
EVALUATION_MANIFEST = "dukascopy_demo_mt5_1_xauusd_m1_20190801_20230801.manifest.toml"
PROVENANCE_ADDENDUM = (
    "dukascopy_demo_mt5_1_xauusd_m1_20190801_20230801"
    ".instrument_specification_provenance.toml"
)
COST_SCENARIOS = (Decimal("0"), Decimal("1"), Decimal("3"))
MINIMUM_QUALIFYING_SESSIONS = 709
WALK_FORWARD_WINDOWS = 5


@dataclass(frozen=True, slots=True)
class Candidate003Dataset:
    path: Path
    source_timezone: str
    point_size: Decimal


@dataclass(frozen=True, slots=True)
class Candidate003Run:
    scenarios: dict[str, tuple[ReplaySessionResult, ...]]
    exclusions: tuple[SkippedSession, ...]
    validation: ResearchValidationReport


def load_frozen_evaluation(
    path: Path, *, manifest: Path, provenance: Path
) -> Candidate003Dataset:
    """Fail closed unless the sole approved Candidate 003 evaluation bundle matches."""
    if path.name != EVALUATION_FILENAME or manifest.name != EVALUATION_MANIFEST:
        raise ValueError("Candidate 003 accepts only its frozen evaluation dataset")
    if provenance.name != PROVENANCE_ADDENDUM:
        raise ValueError(
            "Candidate 003 requires its frozen instrument provenance addendum"
        )
    if "confirmation" in {part.lower() for part in path.parts}:
        raise ValueError("confirmation data is forbidden to the evaluation replay")
    if _digest(path) != EVALUATION_SHA256:
        raise ValueError("evaluation SHA-256 does not match Candidate 003 v0.2")
    with manifest.open("rb") as handle:
        identity = tomllib.load(handle)
    with provenance.open("rb") as handle:
        metadata = tomllib.load(handle)
    if identity["identity"]["sha256"] != EVALUATION_SHA256:
        raise ValueError("manifest SHA-256 mismatch")
    if identity["identity"]["raw_filename"] != EVALUATION_FILENAME:
        raise ValueError("manifest raw filename mismatch")
    if identity["identity"]["role"] != "evaluation":
        raise ValueError("manifest role is not evaluation")
    if identity["time"]["source_timezone"] != "Africa/Lagos":
        raise ValueError("unexpected source timezone")
    bound = metadata["identity"]
    spec = metadata["instrument_specification"]
    if (
        bound["candidate_id"] != CANDIDATE_ID
        or bound["candidate_version"] != CANDIDATE_VERSION
        or bound["raw_sha256"] != EVALUATION_SHA256
        or spec["symbol"] != "XAUUSD"
        or spec["digits"] != 3
        or Decimal(spec["point_size"]) != Decimal("0.001")
    ):
        raise ValueError("frozen Candidate 003 provenance metadata mismatch")
    return Candidate003Dataset(path, "Africa/Lagos", Decimal("0.001"))


def settings(slippage_points: Decimal) -> IntradayMomentumSettings:
    if slippage_points not in COST_SCENARIOS:
        raise ValueError("only frozen 0/+1/+3 point scenarios are permitted")
    return IntradayMomentumSettings(
        timezone="America/New_York",
        signal_start=time(8, 20),
        entry_time=time(8, 25),
        exit_time=time(13, 30),
        signal_window_minutes=5,
        point_size=Decimal("0.001"),
        additional_slippage_points=slippage_points,
    )


def simulate_session(
    bars: Iterable[MinuteBar], *, session_day: date, slippage_points: Decimal
) -> ReplaySessionResult:
    """Execute only the frozen five-minute directional breakout definition."""
    return simulate_intraday_momentum_session(
        bars, session_day=session_day, settings=settings(slippage_points)
    )


def replay_frozen_evaluation(
    dataset: Candidate003Dataset,
    *,
    quality_exclusions: frozenset[date],
    protocol_path: Path,
) -> Candidate003Run:
    """Deterministic evaluation-only replay; the caller must separately authorize it."""
    bars = load_mt5_minute_bars(dataset.path, source_timezone=dataset.source_timezone)
    protocol = load_research_validation_settings(protocol_path)
    outcomes: dict[str, tuple[ReplaySessionResult, ...]] = {}
    skipped: tuple[SkippedSession, ...] | None = None
    for stress in COST_SCENARIOS:
        run = run_intraday_momentum_backtest(
            bars, settings=settings(stress), excluded_session_days=quality_exclusions
        )
        outcomes[str(stress)] = run.results
        skipped = run.skipped_sessions if skipped is None else skipped
    qualifying_count = len(outcomes[str(COST_SCENARIOS[0])])
    if qualifying_count < MINIMUM_QUALIFYING_SESSIONS:
        raise ValueError(
            "Candidate 003 evaluation has fewer than 709 complete qualifying sessions"
        )
    sessions = {
        name: tuple(
            ValidationSession(item.session_day, item.r_multiple) for item in results
        )
        for name, results in outcomes.items()
    }
    validation = run_research_validation(
        sessions,
        holdout_fraction=protocol.holdout_fraction,
        training_sessions=protocol.walk_forward.training_sessions,
        validation_sessions=protocol.walk_forward.validation_sessions,
        step_sessions=protocol.walk_forward.step_sessions,
        gate=protocol.gate,
        maximum_walk_forward_windows=WALK_FORWARD_WINDOWS,
    )
    return Candidate003Run(outcomes, skipped or (), validation)


def _digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
