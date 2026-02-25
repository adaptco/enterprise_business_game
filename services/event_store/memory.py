"""In-memory Event Store implementation for testing and development."""

from collections import defaultdict
from typing import Dict, List
from uuid import UUID

from .domain import Event, EventStore


class MemoryEventStore(EventStore):
    """Dictionary-backed Event Store. Not persistent — intended for tests."""

    def __init__(self) -> None:
        self._events: List[Event] = []
        self._aggregate_events: Dict[UUID, List[Event]] = defaultdict(list)

    async def append(self, event: Event) -> None:
        """Appends an event to the store."""
        self._events.append(event)
        self._aggregate_events[event.aggregate_id].append(event)

    async def get_events(self, aggregate_id: UUID) -> List[Event]:
        """Retrieves all events for a given aggregate, ordered by version."""
        return sorted(
            self._aggregate_events.get(aggregate_id, []),
            key=lambda e: e.version,
        )

    async def get_all_events(self) -> List[Event]:
        """Retrieves all events from the store, ordered by timestamp."""
        return sorted(self._events, key=lambda e: e.timestamp)

