"""Unit tests for MemoryEventStore."""

import asyncio
import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from services.event_store.domain import Event
from services.event_store.memory import MemoryEventStore


class TestMemoryEventStore(unittest.TestCase):
    """Tests for the in-memory EventStore implementation."""

    def setUp(self) -> None:
        self.store = MemoryEventStore()
        self.agg_id = uuid4()

    def _run(self, coro):
        """Helper to run async code in sync tests."""
        return asyncio.get_event_loop().run_until_complete(coro)

    # ------------------------------------------------------------------
    # append / get_events
    # ------------------------------------------------------------------

    def test_append_and_retrieve_single_event(self) -> None:
        event = Event(
            aggregate_id=self.agg_id,
            event_type="ItemCreated",
            payload={"name": "widget"},
        )
        self._run(self.store.append(event))
        events = self._run(self.store.get_events(self.agg_id))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ItemCreated")
        self.assertEqual(events[0].aggregate_id, self.agg_id)

    def test_append_multiple_events_same_aggregate(self) -> None:
        for i in range(5):
            event = Event(
                aggregate_id=self.agg_id,
                event_type=f"Event_{i}",
                payload={"seq": i},
                version=i + 1,
            )
            self._run(self.store.append(event))

        events = self._run(self.store.get_events(self.agg_id))
        self.assertEqual(len(events), 5)
        versions = [e.version for e in events]
        self.assertEqual(versions, [1, 2, 3, 4, 5])

    def test_events_returned_ordered_by_version(self) -> None:
        """Insert out of order; must come back sorted by version."""
        for v in [3, 1, 2]:
            event = Event(
                aggregate_id=self.agg_id,
                event_type="Reordered",
                payload={"v": v},
                version=v,
            )
            self._run(self.store.append(event))

        events = self._run(self.store.get_events(self.agg_id))
        self.assertEqual([e.version for e in events], [1, 2, 3])

    # ------------------------------------------------------------------
    # aggregate isolation
    # ------------------------------------------------------------------

    def test_different_aggregates_are_isolated(self) -> None:
        agg_a, agg_b = uuid4(), uuid4()

        self._run(self.store.append(Event(
            aggregate_id=agg_a, event_type="A", payload={},
        )))
        self._run(self.store.append(Event(
            aggregate_id=agg_b, event_type="B", payload={},
        )))

        events_a = self._run(self.store.get_events(agg_a))
        events_b = self._run(self.store.get_events(agg_b))

        self.assertEqual(len(events_a), 1)
        self.assertEqual(events_a[0].event_type, "A")
        self.assertEqual(len(events_b), 1)
        self.assertEqual(events_b[0].event_type, "B")

    def test_get_events_unknown_aggregate_returns_empty(self) -> None:
        events = self._run(self.store.get_events(uuid4()))
        self.assertEqual(events, [])

    # ------------------------------------------------------------------
    # get_all_events
    # ------------------------------------------------------------------

    def test_get_all_events_returns_all(self) -> None:
        now = datetime.utcnow()
        for i in range(3):
            self._run(self.store.append(Event(
                aggregate_id=uuid4(),
                event_type=f"Global_{i}",
                payload={},
                timestamp=now + timedelta(seconds=i),
            )))

        all_events = self._run(self.store.get_all_events())
        self.assertEqual(len(all_events), 3)

    def test_get_all_events_ordered_by_timestamp(self) -> None:
        now = datetime.utcnow()
        # Insert in reverse chronological order
        for i in [2, 0, 1]:
            self._run(self.store.append(Event(
                aggregate_id=uuid4(),
                event_type=f"T_{i}",
                payload={},
                timestamp=now + timedelta(seconds=i),
            )))

        all_events = self._run(self.store.get_all_events())
        types = [e.event_type for e in all_events]
        self.assertEqual(types, ["T_0", "T_1", "T_2"])

    # ------------------------------------------------------------------
    # Event.to_dict
    # ------------------------------------------------------------------

    def test_event_to_dict_round_trip(self) -> None:
        event = Event(
            aggregate_id=self.agg_id,
            event_type="Serialized",
            payload={"key": "value"},
        )
        d = event.to_dict()

        self.assertEqual(d["event_type"], "Serialized")
        self.assertEqual(d["aggregate_id"], str(self.agg_id))
        self.assertIn("event_id", d)
        self.assertIn("timestamp", d)
        self.assertEqual(d["version"], 1)


if __name__ == "__main__":
    unittest.main()
