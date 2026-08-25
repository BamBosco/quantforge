"""Typed loading of approved research-only backtest configuration."""

from dataclasses import dataclass
from datetime import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
import tomllib

from quantforge.backtest.orb_bias import DirectionalBiasMode, DirectionalBiasSettings


@dataclass(frozen=True, slots=True)
class CostScenario:
    """One explicitly named adverse-slippage sensitivity case."""

    name: str
    additional_slippage_points: Decimal

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("cost scenario name must not be empty")
        if self.additional_slippage_points < 0:
            raise ValueError("cost scenario slippage must not be negative")


@dataclass(frozen=True, slots=True)
class IntradayMomentumProfile:
    """All time-based rules for the approved fixed momentum experiment."""

    timezone: str
    signal_start: time
    entry_time: time
    exit_time: time
    signal_window_minutes: int
    max_completed_entries_per_session: int

    def __post_init__(self) -> None:
        if not self.timezone:
            raise ValueError("strategy timezone must not be empty")
        if not self.signal_start < self.entry_time < self.exit_time:
            raise ValueError("momentum session times must be strictly ordered")
        if self.signal_window_minutes <= 0:
            raise ValueError("momentum signal window must be positive")
        if self.max_completed_entries_per_session != 1:
            raise ValueError("momentum experiment permits exactly one entry per session")


def load_cost_scenarios(path: Path) -> tuple[CostScenario, ...]:
    """Load named cost sensitivity cases from an ORB strategy profile."""
    with path.open("rb") as file:
        raw = tomllib.load(file)
    try:
        scenarios = tuple(
            CostScenario(
                name=str(item["name"]),
                additional_slippage_points=Decimal(
                    str(item["additional_slippage_points"])
                ),
            )
            for item in raw["backtest_cost_sensitivity"]["scenarios"]
        )
    except (KeyError, TypeError, InvalidOperation) as error:
        raise ValueError(
            "invalid ORB backtest cost-sensitivity configuration"
        ) from error
    if not scenarios:
        raise ValueError("at least one cost scenario is required")
    if len({item.name for item in scenarios}) != len(scenarios):
        raise ValueError("cost scenario names must be unique")
    return scenarios


def load_intraday_momentum_profile(path: Path) -> IntradayMomentumProfile:
    """Load frozen session rules from the approved momentum strategy profile."""
    with path.open("rb") as file:
        raw = tomllib.load(file)
    try:
        session = raw["session"]
        profile = IntradayMomentumProfile(
            timezone=str(session["timezone"]),
            signal_start=time.fromisoformat(str(session["signal_start"])),
            entry_time=time.fromisoformat(str(session["entry_time"])),
            exit_time=time.fromisoformat(str(session["exit_time"])),
            signal_window_minutes=int(session["signal_window_minutes"]),
            max_completed_entries_per_session=int(
                session["max_completed_entries_per_session"]
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid intraday-momentum session configuration") from error
    if profile.entry_time.hour * 60 + profile.entry_time.minute - (
        profile.signal_start.hour * 60 + profile.signal_start.minute
    ) != profile.signal_window_minutes:
        raise ValueError("momentum entry time must follow the configured signal window")
    return profile


def load_instrument_point_size(path: Path, instrument: str) -> Decimal:
    """Load point size from the broker profile without duplicating it in config."""
    with path.open("rb") as file:
        raw = tomllib.load(file)
    try:
        point_size = Decimal(str(raw["instruments"][instrument]["point_size"]))
    except (KeyError, TypeError, InvalidOperation) as error:
        raise ValueError(f"invalid point size for instrument {instrument}") from error
    if point_size <= 0:
        raise ValueError("instrument point size must be positive")
    return point_size


def load_directional_bias_settings(path: Path) -> DirectionalBiasSettings | None:
    """Load an optional, versioned directional filter from an ORB profile."""
    with path.open("rb") as file:
        raw = tomllib.load(file)
    try:
        bias = raw.get("filters", {}).get("directional_bias")
        if bias is None:
            return None
        return DirectionalBiasSettings(
            mode=DirectionalBiasMode(str(bias["mode"])),
            start_time=time.fromisoformat(str(bias["start_time"])),
            end_time=time.fromisoformat(str(bias["end_time"])),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid ORB directional-bias configuration") from error
