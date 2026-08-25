"""Quality assessment for read-only MT5 observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from quantforge.infrastructure.mt5.observation_contracts import (
    ObservationEnvelope,
    payload_sha256,
)


@dataclass(frozen=True, slots=True)
class ObservationQualityPolicy:
    max_staleness_seconds: int = 120
    max_future_skew_seconds: int = 5


@dataclass(frozen=True, slots=True)
class QualityAssessment:
    payload_sha256: str
    quality_status: str
    issues: tuple[str, ...]


def assess_observation(
    observation: ObservationEnvelope,
    *,
    received_at_utc: datetime,
    previous_event_time_utc: datetime | None = None,
    previous_payload_sha256: str | None = None,
    policy: ObservationQualityPolicy | None = None,
) -> QualityAssessment:
    """Assess freshness and sequence integrity without discarding audit evidence."""

    if policy is None:
        policy = ObservationQualityPolicy()
    received_at_utc = received_at_utc.astimezone(UTC)
    event_time = observation.observed_at_utc.astimezone(UTC)
    digest = payload_sha256(observation.to_public_payload())
    issues: list[str] = []
    if digest == previous_payload_sha256:
        issues.append("duplicate_payload")
    if (received_at_utc - event_time).total_seconds() > policy.max_staleness_seconds:
        issues.append("stale_data")
    if (event_time - received_at_utc).total_seconds() > policy.max_future_skew_seconds:
        issues.append("future_timestamp")
    if (
        previous_event_time_utc is not None
        and event_time < previous_event_time_utc.astimezone(UTC)
    ):
        issues.append("clock_regression")
    if observation.schema_version == 2:
        quality = observation.payload["data_quality"]
        if quality["missing_data"]:
            issues.append("reported_missing_data")
        if quality["adapter_status"] != "ok":
            issues.append("adapter_reported_problem")

    status = "accepted"
    if "duplicate_payload" in issues:
        status = "duplicate"
    elif issues:
        status = "degraded"
    return QualityAssessment(digest, status, tuple(issues))
