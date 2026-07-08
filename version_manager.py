"""VersionManager — in-memory blueprint versioning and history."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ghostflow.blueprints.models.blueprint import BlueprintStatus, WorkflowBlueprint


@dataclass
class BlueprintVersion:
    version_id: str
    blueprint_id: str
    version_number: int
    status: BlueprintStatus
    snapshot: dict[str, Any]  # full blueprint.to_dict() at this version
    changes: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "blueprint_id": self.blueprint_id,
            "version_number": self.version_number,
            "status": self.status.value,
            "snapshot": self.snapshot,
            "changes": self.changes,
            "created_at": self.created_at,
        }


class VersionManager:
    """Maintains an in-memory version registry for WorkflowBlueprints.

    Immutability rule: once a blueprint is APPROVED, any mutation must first
    call create_version() to preserve the current state.

    Note: In production, back this with a persistent store via StorageService.
    """

    def __init__(self) -> None:
        self._history: dict[str, list[BlueprintVersion]] = {}

    # ── Primary API ───────────────────────────────────────────────────────────

    def create_version(
        self,
        blueprint: WorkflowBlueprint,
        changes: list[str] | None = None,
    ) -> BlueprintVersion:
        version = BlueprintVersion(
            version_id=str(uuid.uuid4()),
            blueprint_id=blueprint.blueprint_id,
            version_number=blueprint.version,
            status=blueprint.status,
            snapshot=blueprint.to_dict(),
            changes=changes or [],
        )
        self._history.setdefault(blueprint.blueprint_id, []).append(version)
        return version

    def get_history(self, blueprint_id: str) -> list[BlueprintVersion]:
        return list(self._history.get(blueprint_id, []))

    def latest_version(self, blueprint_id: str) -> BlueprintVersion | None:
        history = self.get_history(blueprint_id)
        return history[-1] if history else None

    def compare_versions(
        self,
        v1: BlueprintVersion,
        v2: BlueprintVersion,
    ) -> list[str]:
        """Return a human-readable list of differences between two versions."""
        diffs: list[str] = []

        for key in ("status", "version_number", "name", "confidence_score"):
            val1 = v1.snapshot.get(key)
            val2 = v2.snapshot.get(key)
            if val1 != val2:
                diffs.append(f"{key}: {val1!r} → {val2!r}")

        a1 = len(v1.snapshot.get("actions", []))
        a2 = len(v2.snapshot.get("actions", []))
        if a1 != a2:
            diffs.append(f"action_count: {a1} → {a2}")

        c1 = len(v1.snapshot.get("conditions", []))
        c2 = len(v2.snapshot.get("conditions", []))
        if c1 != c2:
            diffs.append(f"condition_count: {c1} → {c2}")

        if not diffs:
            diffs.append("No differences detected.")

        return diffs

    def bump_version(
        self,
        blueprint: WorkflowBlueprint,
        changes: list[str] | None = None,
    ) -> WorkflowBlueprint:
        """Snapshot the current blueprint, then increment its version number.

        Use when an APPROVED blueprint needs to be revised — enforces the
        immutability contract by preserving the old version before mutation.
        """
        self.create_version(blueprint, changes=changes or ["Version bumped."])
        from datetime import datetime

        blueprint.version += 1
        blueprint.status = BlueprintStatus.DRAFT
        blueprint.updated_at = datetime.now(tz=UTC).isoformat()
        return blueprint

    def clear(self) -> None:
        self._history.clear()
