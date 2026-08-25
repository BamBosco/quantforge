"""Small synchronous dispatcher for deterministic in-process workflows."""

from collections import defaultdict
from collections.abc import Callable
from typing import TypeVar

from quantforge.domain.events import DomainEvent

EventT = TypeVar("EventT", bound=DomainEvent)
EventHandler = Callable[[EventT], None]


class EventBus:
    """Dispatch typed events to registered handlers in registration order.

    Persistence is deliberately outside this component; callers journal events
    through an adapter so dispatch stays deterministic and infrastructure-free.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler[DomainEvent]]] = (
            defaultdict(list)
        )

    def subscribe(self, event_type: type[EventT], handler: EventHandler[EventT]) -> None:
        """Register a handler for one exact domain event type."""
        self._handlers[event_type].append(handler)  # type: ignore[arg-type]

    def publish(self, event: DomainEvent) -> None:
        """Synchronously dispatch an event to its exact-type subscribers."""
        for handler in self._handlers[type(event)]:
            handler(event)
