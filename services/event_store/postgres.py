import asyncpg
import json
from datetime import datetime
from typing import List
from uuid import UUID
from .domain import Event, EventStore

class PostgresEventStore(EventStore):
    """PostgreSQL implementation of the Event Store."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        """Establish connection pool to PostgreSQL."""
        self.pool = await asyncpg.create_pool(self.dsn)
        await self._init_schema()

    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()

    async def _init_schema(self):
        """Initialize the database schema."""
        async with self.pool.acquire() as connection:
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id UUID PRIMARY KEY,
                    aggregate_id UUID NOT NULL,
                    event_type VARCHAR(255) NOT NULL,
                    payload JSONB NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    version INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_aggregate_id ON events (aggregate_id);
            """)

    async def append(self, event: Event) -> None:
        """Appends an event to the store."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as connection:
            await connection.execute("""
                INSERT INTO events (event_id, aggregate_id, event_type, payload, timestamp, version)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, event.event_id, event.aggregate_id, event.event_type, json.dumps(event.payload), event.timestamp, event.version)

    async def get_events(self, aggregate_id: UUID) -> List[Event]:
        """Retrieves all events for a given aggregate."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as connection:
            rows = await connection.fetch("""
                SELECT event_id, aggregate_id, event_type, payload, timestamp, version
                FROM events
                WHERE aggregate_id = $1
                ORDER BY version ASC
            """, aggregate_id)

            return [
                Event(
                    event_id=row['event_id'],
                    aggregate_id=row['aggregate_id'],
                    event_type=row['event_type'],
                    payload=json.loads(row['payload']),
                    timestamp=row['timestamp'],
                    version=row['version']
                ) for row in rows
            ]

    async def get_all_events(self) -> List[Event]:
        """Retrieves all events from the store."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as connection:
            rows = await connection.fetch("""
                SELECT event_id, aggregate_id, event_type, payload, timestamp, version
                FROM events
                ORDER BY timestamp ASC
            """)

            return [
                Event(
                    event_id=row['event_id'],
                    aggregate_id=row['aggregate_id'],
                    event_type=row['event_type'],
                    payload=json.loads(row['payload']),
                    timestamp=row['timestamp'],
                    version=row['version']
                ) for row in rows
            ]
