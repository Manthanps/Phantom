from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class AuditLog:
    audit_id: str
    timestamp: str
    actor: str
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details_json: str = field(default_factory=lambda: json.dumps({}))
    created_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    @classmethod
    def create(
        cls,
        actor: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        now = datetime.now(tz=UTC).isoformat()
        return cls(
            audit_id=str(uuid.uuid4()),
            timestamp=now,
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details_json=json.dumps(details or {}),
            created_at=now,
        )

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> AuditLog:
        return cls(
            audit_id=row["audit_id"],
            timestamp=row["timestamp"],
            actor=row["actor"],
            action=row["action"],
            resource_type=row.get("resource_type"),
            resource_id=row.get("resource_id"),
            details_json=row.get("details_json", "{}"),
            created_at=row["created_at"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": json.loads(self.details_json),
            "created_at": self.created_at,
        }

    def to_row(self) -> tuple[Any, ...]:
        return (
            self.audit_id,
            self.timestamp,
            self.actor,
            self.action,
            self.resource_type,
            self.resource_id,
            self.details_json,
            self.created_at,
        )
