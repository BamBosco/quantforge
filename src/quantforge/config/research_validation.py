"""Loading for versioned research-validation protocols."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import tomllib

from quantforge.backtest.validation import ResearchGate


@dataclass(frozen=True, slots=True)
class WalkForwardSettings:
    """Chronological window sizes for a fixed-strategy walk-forward review."""

    training_sessions: int
    validation_sessions: int
    step_sessions: int

    def __post_init__(self) -> None:
        if min(
            self.training_sessions, self.validation_sessions, self.step_sessions
        ) <= 0:
            raise ValueError("walk-forward settings must be positive")


@dataclass(frozen=True, slots=True)
class ResearchValidationSettings:
    """Complete, versioned protocol for one research-validation run."""

    protocol_id: str
    version: str
    holdout_fraction: Decimal
    walk_forward: WalkForwardSettings
    gate: ResearchGate


def load_research_validation_settings(path: Path) -> ResearchValidationSettings:
    """Load a research protocol without hardcoding validation thresholds."""
    with path.open("rb") as file:
        raw = tomllib.load(file)
    try:
        protocol = raw["protocol"]
        split = raw["chronological_split"]
        walk_forward = raw["walk_forward"]
        gate = raw["research_gate"]
        settings = ResearchValidationSettings(
            protocol_id=str(protocol["protocol_id"]),
            version=str(protocol["version"]),
            holdout_fraction=Decimal(str(split["holdout_fraction"])),
            walk_forward=WalkForwardSettings(
                training_sessions=int(walk_forward["training_sessions"]),
                validation_sessions=int(walk_forward["validation_sessions"]),
                step_sessions=int(walk_forward["step_sessions"]),
            ),
            gate=ResearchGate(
                minimum_completed_trades=int(gate["minimum_completed_trades"]),
                require_positive_total_r=bool(gate["require_positive_total_r"]),
                require_positive_mean_r=bool(gate["require_positive_mean_r"]),
                require_positive_holdout=bool(gate["require_positive_holdout"]),
                minimum_positive_walk_forward_windows=int(
                    gate["minimum_positive_walk_forward_windows"]
                ),
            ),
        )
    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
        raise ValueError("invalid research-validation configuration") from error
    if not settings.protocol_id or not settings.version:
        raise ValueError("research-validation protocol ID and version are required")
    if not Decimal("0") < settings.holdout_fraction < Decimal("1"):
        raise ValueError(
            "research-validation holdout fraction must be between zero and one"
        )
    return settings
