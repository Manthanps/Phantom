from __future__ import annotations

from datetime import UTC, datetime

from ghostflow.storage.models.blueprint import Blueprint
from ghostflow.storage.repositories.base_repository import BaseRepository


class BlueprintRepository(BaseRepository):
    """Storage-only repository. Executor logic lives in a future layer."""

    def insert_blueprint(self, blueprint: Blueprint) -> None:
        self.execute(
            """
            INSERT OR IGNORE INTO blueprints
                (blueprint_id, name, version, status, trigger_json, actions_json,
                 rollback_json, confidence, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            blueprint.to_row(),
        )

    def get_blueprint_by_id(self, blueprint_id: str) -> Blueprint | None:
        row = self.fetch_one("SELECT * FROM blueprints WHERE blueprint_id = ?", (blueprint_id,))
        return Blueprint.from_row(row) if row else None

    def list_blueprints(self, limit: int = 100, offset: int = 0) -> list[Blueprint]:
        rows = self.fetch_all(
            "SELECT * FROM blueprints ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [Blueprint.from_row(r) for r in rows]

    def update_blueprint_status(self, blueprint_id: str, status: str) -> None:
        now = datetime.now(tz=UTC).isoformat()
        self.execute(
            "UPDATE blueprints SET status = ?, updated_at = ? WHERE blueprint_id = ?",
            (status, now, blueprint_id),
        )
