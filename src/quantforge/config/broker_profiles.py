"""Configuration-only broker and instrument profiles for infrastructure adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any, Mapping


class BrokerProfileError(ValueError):
    """Raised for malformed non-secret broker profile configuration."""


@dataclass(frozen=True, slots=True)
class InstrumentProfile:
    canonical_instrument: str
    broker_symbol: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class BrokerProfile:
    profile_id: str
    adapter: str
    environment: str
    instruments: tuple[InstrumentProfile, ...]


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BrokerProfileError(f"{name} must be a table")
    return value


def _nonempty(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BrokerProfileError(f"{name} must be a non-empty string")
    return value


def load_broker_profile(path: Path) -> BrokerProfile:
    """Load a profile that contains mappings only, never credentials or tokens."""

    with path.open("rb") as profile_file:
        parsed = tomllib.load(profile_file)
    profile = _mapping(parsed.get("profile"), "profile")
    profile_id = _nonempty(profile.get("id", profile.get("name")), "profile.id")
    adapter = _nonempty(profile.get("adapter", "mt5"), "profile.adapter")
    environment = _nonempty(profile.get("environment", "unspecified"), "profile.environment")
    instruments_raw = _mapping(parsed.get("instruments", {}), "instruments")
    instruments: list[InstrumentProfile] = []
    for canonical, details in instruments_raw.items():
        details_map = _mapping(details, f"instruments.{canonical}")
        instruments.append(
            InstrumentProfile(
                canonical_instrument=_nonempty(canonical, "instrument name"),
                broker_symbol=_nonempty(
                    details_map.get("broker_symbol", details_map.get("symbol", canonical)),
                    f"instruments.{canonical}.broker_symbol",
                ),
                enabled=bool(details_map.get("enabled", True)),
            )
        )
    return BrokerProfile(profile_id, adapter, environment, tuple(instruments))
