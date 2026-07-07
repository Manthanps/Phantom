"""Lightweight migration manager for GhostFlow SQLite schema."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from ghostflow.plugins.buildnext.storage.schemas import (
    IDEAS_INDEXES,
    IDEAS_TABLE,
    MEMORY_INDEXES,
    MEMORY_TABLE,
    USER_PROFILE_INDEXES,
    USER_PROFILE_TABLE,
)
from ghostflow.storage.schemas import (
    AGENT_EXECUTIONS_INDEXES,
    AGENT_EXECUTIONS_TABLE,
    AGENTS_INDEXES,
    AGENTS_TABLE,
    AUDIT_LOGS_INDEXES,
    AUDIT_LOGS_TABLE,
    BLUEPRINTS_INDEXES,
    BLUEPRINTS_TABLE,
    EVENTS_INDEXES,
    EVENTS_TABLE,
    EXCEPTION_RULES_INDEXES,
    EXCEPTION_RULES_TABLE,
    METRICS_INDEXES,
    METRICS_TABLE,
    MIGRATIONS_TABLE,
    PERSISTED_POLICIES_INDEXES,
    PERSISTED_POLICIES_TABLE,
    PLUGINS_INDEXES,
    PLUGINS_TABLE,
    REJECTION_HISTORY_INDEXES,
    REJECTION_HISTORY_TABLE,
    SESSIONS_INDEXES,
    SESSIONS_TABLE,
    WORKFLOW_CANDIDATES_INDEXES,
    WORKFLOW_CANDIDATES_TABLE,
    WORKFLOW_DEFINITIONS_INDEXES,
    WORKFLOW_DEFINITIONS_TABLE,
    WORKFLOW_EXECUTIONS_INDEXES,
    WORKFLOW_EXECUTIONS_TABLE,
)
from ghostflow.storage.sqlite_manager import SQLiteManager

logger = logging.getLogger(__name__)

# ── Migration registry ────────────────────────────────────────────────────────
# Each entry is (name, list_of_sql_statements).
# Add new migrations by appending — never edit existing ones.

_MIGRATIONS: list[tuple[str, list[str]]] = [
    (
        "001_initial_schema",
        [
            MIGRATIONS_TABLE,
            EVENTS_TABLE,
            *EVENTS_INDEXES,
            SESSIONS_TABLE,
            *SESSIONS_INDEXES,
            WORKFLOW_CANDIDATES_TABLE,
            *WORKFLOW_CANDIDATES_INDEXES,
            BLUEPRINTS_TABLE,
            *BLUEPRINTS_INDEXES,
            AUDIT_LOGS_TABLE,
            *AUDIT_LOGS_INDEXES,
        ],
    ),
    (
        "002_exception_learning",
        [
            REJECTION_HISTORY_TABLE,
            *REJECTION_HISTORY_INDEXES,
            EXCEPTION_RULES_TABLE,
            *EXCEPTION_RULES_INDEXES,
        ],
    ),
    (
        "003_buildnext_tables",
        [
            IDEAS_TABLE,
            *IDEAS_INDEXES,
            USER_PROFILE_TABLE,
            *USER_PROFILE_INDEXES,
            MEMORY_TABLE,
            *MEMORY_INDEXES,
        ],
    ),
    (
        "004_workflow_composer",
        [
            WORKFLOW_DEFINITIONS_TABLE,
            *WORKFLOW_DEFINITIONS_INDEXES,
            WORKFLOW_EXECUTIONS_TABLE,
            *WORKFLOW_EXECUTIONS_INDEXES,
        ],
    ),
    (
        "005_persistence_layer",
        [
            PERSISTED_POLICIES_TABLE,
            *PERSISTED_POLICIES_INDEXES,
            AGENT_EXECUTIONS_TABLE,
            *AGENT_EXECUTIONS_INDEXES,
        ],
    ),
    (
        "006_platform_persistence_records",
        [
            PLUGINS_TABLE,
            *PLUGINS_INDEXES,
            AGENTS_TABLE,
            *AGENTS_INDEXES,
            METRICS_TABLE,
            *METRICS_INDEXES,
        ],
    ),
]


class MigrationManager:
    """Tracks and applies database migrations idempotently.

    Usage::

        mgr = MigrationManager(sqlite_manager)
        applied = mgr.apply_pending()
    """

    def __init__(self, manager: SQLiteManager) -> None:
        self._manager = manager

    def apply_pending(self) -> list[str]:
        """Create _migrations table if absent, then apply all unapplied migrations.

        Returns the names of newly applied migrations.
        """
        self._ensure_tracking_table()

        applied = self._applied_names()
        newly_applied: list[str] = []

        for index, (name, statements) in enumerate(_MIGRATIONS, start=1):
            if name in applied:
                logger.debug("Migration already applied: %s", name)
                continue

            logger.info("Applying migration: %s", name)
            checksum = self._checksum(statements)
            with self._manager.transaction() as conn:
                for sql in statements:
                    conn.execute(sql)
                conn.execute(
                    """
                    INSERT INTO _migrations
                        (migration_id, name, applied_at, checksum)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        f"{index:03d}",
                        name,
                        datetime.now(tz=UTC).isoformat(),
                        checksum,
                    ),
                )
            newly_applied.append(name)
            logger.info("Migration applied: %s", name)

        return newly_applied

    def list_applied(self) -> list[dict[str, Any]]:
        self._ensure_tracking_table()
        cursor = self._manager.execute(
            """
            SELECT migration_id, name, applied_at, checksum
            FROM _migrations
            ORDER BY id
            """
        )
        return [
            {
                "migration_id": row["migration_id"] or "",
                "name": row["name"],
                "applied_at": row["applied_at"],
                "checksum": row["checksum"] or "",
            }
            for row in cursor.fetchall()
        ]

    def list_available(self) -> list[dict[str, Any]]:
        """Return all registered migrations with deterministic checksums."""
        return [
            {
                "migration_id": f"{index:03d}",
                "name": name,
                "checksum": self._checksum(statements),
            }
            for index, (name, statements) in enumerate(_MIGRATIONS, start=1)
        ]

    def pending(self) -> list[dict[str, Any]]:
        """Return migrations that are registered but not applied."""
        applied = self._applied_names()
        return [m for m in self.list_available() if m["name"] not in applied]

    def table_names(self) -> list[str]:
        cursor = self._manager.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row["name"] for row in cursor.fetchall()]

    # ── Internal ───────────────────────────────────────────────────────────────

    def _applied_names(self) -> set[str]:
        self._ensure_tracking_table()
        try:
            cursor = self._manager.execute("SELECT name FROM _migrations")
            return {row["name"] for row in cursor.fetchall()}
        except Exception:
            return set()

    def _ensure_tracking_table(self) -> None:
        """Create or upgrade the migration tracking table.

        Older GhostFlow databases only tracked ``name`` and ``applied_at``.
        This method adds checksum columns in-place so existing installs keep
        working without a destructive rebuild.
        """
        with self._manager.transaction() as conn:
            conn.execute(MIGRATIONS_TABLE)
            columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(_migrations)").fetchall()
            }
            if "migration_id" not in columns:
                conn.execute("ALTER TABLE _migrations ADD COLUMN migration_id TEXT")
            if "checksum" not in columns:
                conn.execute("ALTER TABLE _migrations ADD COLUMN checksum TEXT NOT NULL DEFAULT ''")

            rows = conn.execute(
                "SELECT id, name FROM _migrations WHERE migration_id IS NULL OR checksum = ''"
            ).fetchall()
            available = {
                name: (f"{index:03d}", self._checksum(statements))
                for index, (name, statements) in enumerate(_MIGRATIONS, start=1)
            }
            for row in rows:
                migration_id, checksum = available.get(row["name"], ("", ""))
                conn.execute(
                    """
                    UPDATE _migrations
                    SET migration_id = COALESCE(NULLIF(migration_id, ''), ?),
                        checksum = COALESCE(NULLIF(checksum, ''), ?)
                    WHERE id = ?
                    """,
                    (migration_id, checksum, row["id"]),
                )

    @staticmethod
    def _checksum(statements: list[str]) -> str:
        payload = "\n\n".join(statement.strip() for statement in statements)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
