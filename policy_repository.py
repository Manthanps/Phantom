"""PolicyRepository — persists Policy objects to the persisted_policies table."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ghostflow.storage.repositories.base_repository import BaseRepository


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


class PolicyRepository(BaseRepository):
    """CRUD for the persisted_policies table."""

    def insert(self, policy_dict: dict[str, Any]) -> None:
        now = _now()
        self.execute(
            """
            INSERT OR REPLACE INTO persisted_policies
                (policy_id, name, description, effect,
                 principals_json, permissions_json, resources_json,
                 conditions_json, priority, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                policy_dict["policy_id"],
                policy_dict["name"],
                policy_dict.get("description", ""),
                policy_dict["effect"],
                json.dumps(policy_dict.get("principals", [])),
                json.dumps(policy_dict.get("permissions", [])),
                json.dumps(policy_dict.get("resources", ["*"])),
                json.dumps(policy_dict.get("conditions", {})),
                policy_dict.get("priority", 0),
                1 if policy_dict.get("is_active", True) else 0,
                policy_dict.get("created_at", now),
                now,
            ),
        )

    def update_active(self, policy_id: str, is_active: bool) -> None:
        self.execute(
            "UPDATE persisted_policies SET is_active = ?, updated_at = ? WHERE policy_id = ?",
            (1 if is_active else 0, _now(), policy_id),
        )

    def delete(self, policy_id: str) -> None:
        self.execute(
            "DELETE FROM persisted_policies WHERE policy_id = ?",
            (policy_id,),
        )

    def get(self, policy_id: str) -> dict[str, Any] | None:
        row = self.fetch_one(
            "SELECT * FROM persisted_policies WHERE policy_id = ?",
            (policy_id,),
        )
        return self._row_to_dict(row) if row else None

    def list_all(self, active_only: bool = False) -> list[dict[str, Any]]:
        if active_only:
            rows = self.fetch_all(
                "SELECT * FROM persisted_policies WHERE is_active = 1 ORDER BY priority DESC"
            )
        else:
            rows = self.fetch_all("SELECT * FROM persisted_policies ORDER BY priority DESC")
        return [self._row_to_dict(r) for r in rows]

    def count(self) -> int:
        row = self.fetch_one("SELECT COUNT(*) AS cnt FROM persisted_policies")
        return row["cnt"] if row else 0

    @staticmethod
    def _row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "policy_id": row["policy_id"],
            "name": row["name"],
            "description": row["description"],
            "effect": row["effect"],
            "principals": json.loads(row["principals_json"]),
            "permissions": json.loads(row["permissions_json"]),
            "resources": json.loads(row["resources_json"]),
            "conditions": json.loads(row["conditions_json"]),
            "priority": row["priority"],
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
