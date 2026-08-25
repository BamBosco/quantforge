"""Deterministic event replay and execution simulation."""

from quantforge.backtest.orb_simulation import (
    OrbSessionResult,
    OrbSimulationSettings,
    SessionOutcome,
    simulate_orb_session,
)
from quantforge.backtest.orb_runner import OrbBacktestRun, run_orb_backtest
from quantforge.backtest.intraday_momentum_runner import (
    IntradayMomentumBacktestRun,
    run_intraday_momentum_backtest,
)
from quantforge.backtest.orb_bias import DirectionalBiasSettings, EntryEligibility
from quantforge.backtest.validation import (
    ResearchGate,
    ResearchValidationReport,
    ValidationSession,
    run_research_validation,
)

__all__ = [
    "OrbSessionResult",
    "OrbSimulationSettings",
    "OrbBacktestRun",
    "IntradayMomentumBacktestRun",
    "DirectionalBiasSettings",
    "EntryEligibility",
    "ResearchGate",
    "ResearchValidationReport",
    "SessionOutcome",
    "ValidationSession",
    "run_orb_backtest",
    "run_intraday_momentum_backtest",
    "run_research_validation",
    "simulate_orb_session",
]
