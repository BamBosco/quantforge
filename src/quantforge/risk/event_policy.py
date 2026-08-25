"""Risk-Engine evaluation of validated scheduled economic-calendar events."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID

from quantforge.config.event_risk import EventRiskPolicySettings
from quantforge.domain.events import EventRiskDecisionRecorded
from quantforge.market_data.economic_calendar import CalendarEvent, CalendarSnapshot


class EventRiskAction(StrEnum):
    """Actions that downstream components may take after Risk Engine approval."""

    ALLOW = "allow"
    REJECT_NEW_INTENTS = "reject_new_intents"
    CANCEL_PENDING_ENTRIES = "cancel_pending_entries"
    FLATTEN_OPEN_POSITION = "flatten_open_position"


@dataclass(frozen=True, slots=True)
class EventRiskDecision:
    """An auditable, unsized decision for one instrument at one instant."""

    instrument: str
    policy_id: str
    policy_version: str
    calendar_snapshot_id: str
    actions: frozenset[EventRiskAction]
    reason: str
    event: CalendarEvent | None = None
    blackout_starts_at: datetime | None = None

    @property
    def allows_new_intents(self) -> bool:
        """State whether the Risk Engine may approve another entry intent."""
        return EventRiskAction.REJECT_NEW_INTENTS not in self.actions

    def to_audit_event(
        self,
        *,
        correlation_id: UUID,
        occurred_at: datetime,
    ) -> EventRiskDecisionRecorded:
        """Create the immutable domain record that a journal can persist."""
        return EventRiskDecisionRecorded(
            correlation_id=correlation_id,
            occurred_at=occurred_at,
            instrument=self.instrument,
            policy_id=self.policy_id,
            policy_version=self.policy_version,
            calendar_snapshot_id=self.calendar_snapshot_id,
            actions=tuple(sorted(action.value for action in self.actions)),
            reason=self.reason,
            provider_event_id=(self.event.provider_event_id if self.event else None),
            blackout_starts_at=self.blackout_starts_at,
        )


class EventRiskPolicy:
    """Fail-closed scheduled-event risk control owned by the Risk Engine."""

    def __init__(self, settings: EventRiskPolicySettings) -> None:
        self._settings = settings

    def evaluate(
        self,
        *,
        instrument: str,
        evaluated_at: datetime,
        calendar: CalendarSnapshot | None,
        manually_released_event_ids: frozenset[str] = frozenset(),
    ) -> EventRiskDecision:
        """Return entry, cancellation, and flattening controls for an instrument."""
        _require_utc(evaluated_at, "evaluated_at")
        if instrument not in self._settings.covered_event_types:
            return self._allow(
                instrument, calendar, "instrument is outside event-risk scope"
            )
        if calendar is None:
            return self._calendar_failure(
                instrument, "calendar snapshot is unavailable"
            )
        if evaluated_at - calendar.retrieved_at > self._settings.maximum_calendar_age:
            return self._calendar_failure(
                instrument, "calendar snapshot is stale", calendar
            )

        covered_events = self._covered_events(instrument, calendar)
        active_event = self._active_event(
            covered_events, evaluated_at, manually_released_event_ids
        )
        if active_event is None:
            return self._allow(instrument, calendar, "no active covered event blackout")

        blackout_starts_at = (
            active_event.scheduled_at - self._settings.blackout_before_event
        )
        if evaluated_at < active_event.scheduled_at:
            return self._blocked(
                instrument,
                calendar,
                active_event,
                blackout_starts_at,
                "scheduled-event blackout is active",
                flatten=True,
            )
        return self._blocked(
            instrument,
            calendar,
            active_event,
            blackout_starts_at,
            "post-event manual release is required",
            flatten=False,
        )

    def _covered_events(
        self, instrument: str, calendar: CalendarSnapshot
    ) -> tuple[CalendarEvent, ...]:
        covered_types = self._settings.covered_event_types[instrument]
        return tuple(
            event
            for event in calendar.events
            if event.canonical_event_type in covered_types
        )

    def _active_event(
        self,
        events: tuple[CalendarEvent, ...],
        evaluated_at: datetime,
        manually_released_event_ids: frozenset[str],
    ) -> CalendarEvent | None:
        candidates = tuple(
            event
            for event in events
            if self._event_is_active(event, evaluated_at, manually_released_event_ids)
        )
        if not candidates:
            return None
        return max(candidates, key=lambda event: event.scheduled_at)

    def _event_is_active(
        self,
        event: CalendarEvent,
        evaluated_at: datetime,
        manually_released_event_ids: frozenset[str],
    ) -> bool:
        """Keep future blackouts active even if an operator released an older event."""
        if evaluated_at < event.scheduled_at - self._settings.blackout_before_event:
            return False
        if evaluated_at < event.scheduled_at:
            return True
        return (
            self._settings.requires_manual_post_event_release
            and event.provider_event_id not in manually_released_event_ids
        )

    def _allow(
        self, instrument: str, calendar: CalendarSnapshot | None, reason: str
    ) -> EventRiskDecision:
        return EventRiskDecision(
            instrument=instrument,
            policy_id=self._settings.policy_id,
            policy_version=self._settings.version,
            calendar_snapshot_id=calendar.snapshot_id if calendar else "unavailable",
            actions=frozenset({EventRiskAction.ALLOW}),
            reason=reason,
        )

    def _calendar_failure(
        self,
        instrument: str,
        reason: str,
        calendar: CalendarSnapshot | None = None,
    ) -> EventRiskDecision:
        return EventRiskDecision(
            instrument=instrument,
            policy_id=self._settings.policy_id,
            policy_version=self._settings.version,
            calendar_snapshot_id=calendar.snapshot_id if calendar else "unavailable",
            actions=frozenset(
                {
                    EventRiskAction.REJECT_NEW_INTENTS,
                    EventRiskAction.CANCEL_PENDING_ENTRIES,
                }
            ),
            reason=reason,
        )

    def _blocked(
        self,
        instrument: str,
        calendar: CalendarSnapshot,
        event: CalendarEvent,
        blackout_starts_at: datetime,
        reason: str,
        *,
        flatten: bool,
    ) -> EventRiskDecision:
        actions = {
            EventRiskAction.REJECT_NEW_INTENTS,
            EventRiskAction.CANCEL_PENDING_ENTRIES,
        }
        if flatten:
            actions.add(EventRiskAction.FLATTEN_OPEN_POSITION)
        return EventRiskDecision(
            instrument=instrument,
            policy_id=self._settings.policy_id,
            policy_version=self._settings.version,
            calendar_snapshot_id=calendar.snapshot_id,
            actions=frozenset(actions),
            reason=reason,
            event=event,
            blackout_starts_at=blackout_starts_at,
        )


def _require_utc(value: datetime, field_name: str) -> None:
    """Reject naive and non-UTC policy timestamps."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
