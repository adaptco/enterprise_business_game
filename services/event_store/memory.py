from typing import List, Dict
from uuid import UUID
from .domain import Event, EventStore

class MemoryEventStore(EventStore):
    """In-memory implementation of the Event Store for testing."""

    def __init__(self):
        self._events: List[Event] = []
        self._aggregate_events: Dict[UUID, List[Event]] = {}

    async def append(self, event: Event) -> None:
        """Appends an event to the store."""
        self._events.append(event)
        if event.aggregate_id not in self._aggregate_events:
            self._aggregate_events[event.aggregate_id] = []
        self._aggregate_events[event.aggregate_id].append(event)

    async def get_events(self, aggregate_id: UUID) -> List[Event]:
        """Retrieves all events for a given aggregate."""
        return self._aggregate_events.get(aggregate_id, [])

    async def get_all_events(self) -> List[Event]:
        """Retrieves all events from the store."""
        return self._events
