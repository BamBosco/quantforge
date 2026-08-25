"""Loading for versioned scheduled-event risk policy configuration."""

import tomllib
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EventRiskPolicySettings:
    """Configuration consumed by the Risk Engine's event-risk policy."""

    policy_id: str
    version: str
    blackout_before_event: timedelta
    maximum_calendar_age: timedelta
    requires_manual_post_event_release: bool
    covered_event_types: dict[str, frozenset[str]]

    def __post_init__(self) -> None:
        if not self.policy_id or not self.version:
            raise ValueError("event-risk policy ID and version are required")
        if self.blackout_before_event <= timedelta(0):
            raise ValueError("event-risk blackout must be positive")
        if self.maximum_calendar_age <= timedelta(0):
            raise ValueError("maximum calendar age must be positive")
        if not self.covered_event_types:
            raise ValueError("at least one instrument event scope is required")
        for instrument, event_types in self.covered_event_types.items():
            if not instrument or not event_types:
                raise ValueError(
                    "each event-risk scope requires an instrument and event types"
                )


def load_event_risk_policy(path: Path) -> EventRiskPolicySettings:
    """Load a policy without embedding event windows or event types in code."""
    with path.open("rb") as file:
        raw = tomllib.load(file)
    try:
        policy = raw["policy"]
        scopes = raw["scope"]
        covered_event_types = {
            str(scope["instrument"]): frozenset(
                str(value) for value in scope["event_types"]
            )
            for scope in scopes
        }
        if len(covered_event_types) != len(scopes):
            raise ValueError("event-risk scope instruments must be unique")
        return EventRiskPolicySettings(
            policy_id=str(policy["policy_id"]),
            version=str(policy["version"]),
            blackout_before_event=timedelta(
                minutes=int(policy["blackout_minutes_before_event"])
            ),
            maximum_calendar_age=timedelta(
                minutes=int(policy["maximum_calendar_age_minutes"])
            ),
            requires_manual_post_event_release=bool(
                policy["requires_manual_post_event_release"]
            ),
            covered_event_types=covered_event_types,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid event-risk policy configuration") from error
