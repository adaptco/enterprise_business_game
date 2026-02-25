from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

@dataclass
class Event:
    """Represents a domain event."""
    aggregate_id: UUID
    event_type: str
    payload: Dict[str, Any]
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "aggregate_id": str(self.aggregate_id),
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
        }

class EventStore(ABC):
    """Abstract base class for Event Store implementations."""

    @abstractmethod
    async def append(self, event: Event) -> None:
        """Appends an event to the store."""
        pass

    @abstractmethod
    async def get_events(self, aggregate_id: UUID) -> List[Event]:
        """Retrieves all events for a given aggregate."""
        pass

    @abstractmethod
    async def get_all_events(self) -> List[Event]:
        """Retrieves all events from the store."""
        pass
