from __future__ import annotations

from typing import Any

from ghostflow.storage.models.stored_event import StoredEvent
from ghostflow.storage.repositories.base_repository import BaseRepository


class EventRepository(BaseRepository):
    def insert_event(self, event: StoredEvent) -> None:
        self.execute(
            """
            INSERT OR IGNORE INTO events
                (event_id, session_id, timestamp, event_type, source,
                 path, old_path, observer_name, host_name, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            event.to_row(),
        )

    def get_event_by_id(self, event_id: str) -> StoredEvent | None:
        row = self.fetch_one("SELECT * FROM events WHERE event_id = ?", (event_id,))
        return StoredEvent.from_row(row) if row else None

    def list_events(self, limit: int = 100, offset: int = 0) -> list[StoredEvent]:
        rows = self.fetch_all(
            "SELECT * FROM events ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [StoredEvent.from_row(r) for r in rows]

    def list_events_by_session(self, session_id: str) -> list[StoredEvent]:
        rows = self.fetch_all(
            "SELECT * FROM events WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,),
        )
        return [StoredEvent.from_row(r) for r in rows]

    def filter_events(
        self,
        event_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        path_contains: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoredEvent]:
        clauses: list[str] = []
        params: list[Any] = []

        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if start_date:
            clauses.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("timestamp <= ?")
            params.append(end_date)
        if path_contains:
            clauses.append("path LIKE ?")
            params.append(f"%{path_contains}%")
        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.extend([limit, offset])

        rows = self.fetch_all(
            f"SELECT * FROM events {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            tuple(params),
        )
        return [StoredEvent.from_row(r) for r in rows]

    def count_events(self) -> int:
        row = self.fetch_one("SELECT COUNT(*) AS cnt FROM events")
        return row["cnt"] if row else 0
