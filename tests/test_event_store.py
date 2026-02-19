import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from services.event_store.domain import Event
from services.event_store.memory import MemoryEventStore

@pytest.mark.asyncio
async def test_memory_event_store():
    store = MemoryEventStore()
    aggregate_id = uuid4()
    
    event1 = Event(aggregate_id=aggregate_id, event_type="TEST_CREATED", payload={"foo": "bar"}, version=1)
    await store.append(event1)
    
    events = await store.get_events(aggregate_id)
    assert len(events) == 1
    assert events[0].payload["foo"] == "bar"

    event2 = Event(aggregate_id=aggregate_id, event_type="TEST_UPDATED", payload={"foo": "baz"}, version=2)
    await store.append(event2)
    
    events = await store.get_events(aggregate_id)
    assert len(events) == 2
    assert events[1].event_type == "TEST_UPDATED"

@pytest.mark.asyncio
async def test_all_events():
    store = MemoryEventStore()
    id1 = uuid4()
    id2 = uuid4()
    
    await store.append(Event(aggregate_id=id1, event_type="A", payload={}, version=1))
    await store.append(Event(aggregate_id=id2, event_type="B", payload={}, version=1))
    
    all_events = await store.get_all_events()
    assert len(all_events) == 2
