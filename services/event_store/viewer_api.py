from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import asyncio

# Import domain classes
from domain import Event, EventStore

app = FastAPI(title="Event Store Viewer API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development convenience
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MockEventStore(EventStore):
    """In-memory Event Store for demonstration."""

    def __init__(self):
        self.events: List[Event] = []
        self._seed_data()

    def _seed_data(self):
        """Populate store with sample events."""
        agg_id_1 = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
        agg_id_2 = UUID("b1eebc99-9c0b-4ef8-bb6d-6bb9bd380b22")
        
        base_time = datetime.utcnow()

        self.events.extend([
            Event(
                aggregate_id=agg_id_1,
                event_type="UserRegistered",
                payload={"username": "jdoe", "email": "jdoe@example.com"},
                timestamp=base_time - timedelta(days=2),
                version=1
            ),
            Event(
                aggregate_id=agg_id_1,
                event_type="UserVerified",
                payload={"method": "email"},
                timestamp=base_time - timedelta(days=1, hours=23),
                version=2
            ),
             Event(
                aggregate_id=agg_id_2,
                event_type="OrderPlaced",
                payload={"product_id": "prod_123", "amount": 99.99},
                timestamp=base_time - timedelta(hours=5),
                version=1
            ),
            Event(
                aggregate_id=agg_id_2,
                event_type="PaymentProcessed",
                payload={"status": "success", "transaction_id": "tx_987"},
                timestamp=base_time - timedelta(hours=4, minutes=55),
                version=2
            ),
             Event(
                aggregate_id=agg_id_2,
                event_type="OrderShipped",
                payload={"carrier": "FedEx", "tracking": "FE123456"},
                timestamp=base_time - timedelta(hours=1),
                version=3
            ),
        ])

    async def append(self, event: Event) -> None:
        self.events.append(event)

    async def get_events(self, aggregate_id: UUID) -> List[Event]:
        return [e for e in self.events if e.aggregate_id == aggregate_id]

    async def get_all_events(self) -> List[Event]:
        return sorted(self.events, key=lambda e: e.timestamp, reverse=True)

# Initialize Mock Store
store = MockEventStore()

@app.get("/api/events", response_model=List[dict])
async def get_all_events():
    """Get all events, sorted by timestamp descending."""
    events = await store.get_all_events()
    return [e.to_dict() for e in events]

@app.get("/api/events/{aggregate_id}", response_model=List[dict])
async def get_events_by_aggregate(aggregate_id: UUID):
    """Get events filter by Aggregate ID."""
    events = await store.get_events(aggregate_id)
    return [e.to_dict() for e in events]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
