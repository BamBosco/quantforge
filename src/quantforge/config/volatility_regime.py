"""Loading for the frozen XAUUSD intraday-volatility research configuration."""

from dataclasses import dataclass
from datetime import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
import tomllib

from quantforge.analytics.intraday_volatility import VolatilityRegimeSettings


@dataclass(frozen=True, slots=True)
class VolatilityRegimeConfiguration:
    """Identity plus typed settings for an offline volatility study."""

    study_id: str
    version: str
    settings: VolatilityRegimeSettings


def load_volatility_regime_configuration(path: Path) -> VolatilityRegimeConfiguration:
    """Load the research study without embedding its constants in code."""
    with path.open("rb") as file:
        raw = tomllib.load(file)
    try:
        identity = raw["identity"]
        session = raw["session"]
        forecaster = raw["forecaster"]
        validation = raw["validation"]
        settings = VolatilityRegimeSettings(
            timezone=str(session["timezone"]),
            predictor_start=time.fromisoformat(str(session["predictor_start"])),
            predictor_end=time.fromisoformat(str(session["predictor_end"])),
            outcome_end=time.fromisoformat(str(session["outcome_end"])),
            training_sessions=int(forecaster["training_sessions"]),
            validation_sessions=int(forecaster["validation_sessions"]),
            validation_step_sessions=int(forecaster["validation_step_sessions"]),
            minimum_bucket_sessions=int(forecaster["minimum_bucket_sessions"]),
            minimum_scored_sessions=int(validation["minimum_scored_sessions"]),
            minimum_improvement=Decimal(str(validation["minimum_improvement"])),
            minimum_positive_windows=int(validation["minimum_positive_windows"]),
            holdout_fraction=Decimal(str(validation["holdout_fraction"])),
        )
        configuration = VolatilityRegimeConfiguration(
            study_id=str(identity["study_id"]),
            version=str(identity["version"]),
            settings=settings,
        )
    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
        raise ValueError("invalid volatility-regime configuration") from error
    if not configuration.study_id or not configuration.version:
        raise ValueError("volatility-regime identity must not be empty")
    return configuration
