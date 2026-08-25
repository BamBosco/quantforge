"""Reproducible runner for the offline XAUUSD volatility-regime study."""

from dataclasses import dataclass
from pathlib import Path

from quantforge.analytics.intraday_volatility import (
    VolatilityValidationReport,
    build_volatility_observations,
    validate_volatility_regime,
)
from quantforge.backtest.dataset import (
    DatasetManifest,
    load_dataset_manifest,
    verify_dataset_checksum,
)
from quantforge.config.volatility_regime import (
    VolatilityRegimeConfiguration,
    load_volatility_regime_configuration,
)
from quantforge.market_data import load_mt5_minute_bars


@dataclass(frozen=True, slots=True)
class VolatilityRegimeStudyRun:
    """Verified dataset identity, frozen configuration, and offline result."""

    manifest: DatasetManifest
    configuration: VolatilityRegimeConfiguration
    report: VolatilityValidationReport


def run_volatility_regime_study(
    *, data_path: Path, manifest_path: Path, configuration_path: Path
) -> VolatilityRegimeStudyRun:
    """Run only after verifying the raw export against its immutable manifest."""
    manifest = load_dataset_manifest(manifest_path)
    if manifest.instrument != "XAUUSD":
        raise ValueError("volatility-regime study requires an XAUUSD dataset")
    verify_dataset_checksum(data_path, manifest)
    configuration = load_volatility_regime_configuration(configuration_path)
    bars = load_mt5_minute_bars(data_path, source_timezone=manifest.source_timezone)
    observations, excluded_sessions = build_volatility_observations(
        bars,
        settings=configuration.settings,
        excluded_session_days=manifest.excluded_session_days,
    )
    report = validate_volatility_regime(
        observations,
        excluded_sessions=excluded_sessions,
        settings=configuration.settings,
    )
    return VolatilityRegimeStudyRun(
        manifest=manifest, configuration=configuration, report=report
    )
