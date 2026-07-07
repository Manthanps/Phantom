"""StorageService — integration boundary between Observer Layer and Storage Layer."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ghostflow.storage.migrations import MigrationManager
from ghostflow.storage.models.audit_log import AuditLog
from ghostflow.storage.models.stored_event import StoredEvent
from ghostflow.storage.models.stored_session import StoredSession
from ghostflow.storage.repositories.agent_execution_repository import AgentExecutionRepository
from ghostflow.storage.repositories.audit_log_repository import AuditLogRepository
from ghostflow.storage.repositories.blueprint_repository import BlueprintRepository
from ghostflow.storage.repositories.event_repository import EventRepository
from ghostflow.storage.repositories.policy_repository import PolicyRepository
from ghostflow.storage.repositories.session_repository import SessionRepository
from ghostflow.storage.repositories.workflow_candidate_repository import WorkflowCandidateRepository
from ghostflow.storage.repositories.workflow_composer_repository import (
    WorkflowDefinitionRepository,
    WorkflowExecutionRepository,
)
from ghostflow.storage.sqlite_manager import SQLiteManager

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path(__file__).parent.parent.parent / "data" / "ghostflow.db"


class StorageService:
    """Orchestrates the Storage Layer.

    Acts as the sole entry point for the Observer Layer sink::

        storage = StorageService()
        storage.initialize()

        observer_service.add_sink("storage", storage.ingest_event)
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        resolved = Path(db_path) if db_path else _DEFAULT_DB
        resolved.parent.mkdir(parents=True, exist_ok=True)

        self._manager = SQLiteManager(resolved)
        self._migrations = MigrationManager(self._manager)

        # Repositories — created after connect() in initialize()
        self._events: EventRepository | None = None
        self._sessions: SessionRepository | None = None
        self._candidates: WorkflowCandidateRepository | None = None
        self._blueprints: BlueprintRepository | None = None
        self._audit: AuditLogRepository | None = None
        self._policies: PolicyRepository | None = None
        self._agent_executions: AgentExecutionRepository | None = None
        self._workflow_definitions: WorkflowDefinitionRepository | None = None
        self._workflow_executions: WorkflowExecutionRepository | None = None
        self._ideas: Any = None
        self._user_profiles: Any = None
        self._memory: Any = None
        self._plugins: Any = None
        self._agents: Any = None
        self._metrics: Any = None
        self._workflows: Any = None
        self._executions: Any = None
        self._audit_facade: Any = None
        self._initialized = False

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Connect, run migrations, wire repositories."""
        if self._initialized:
            return
        self._manager.connect()
        applied = self._migrations.apply_pending()

        self._events = EventRepository(self._manager)
        self._sessions = SessionRepository(self._manager)
        self._candidates = WorkflowCandidateRepository(self._manager)
        self._blueprints = BlueprintRepository(self._manager)
        self._audit = AuditLogRepository(self._manager)
        self._policies = PolicyRepository(self._manager)
        self._agent_executions = AgentExecutionRepository(self._manager)
        self._workflow_definitions = WorkflowDefinitionRepository(self._manager)
        self._workflow_executions = WorkflowExecutionRepository(self._manager)

        from ghostflow.core.persistence.repositories import (
            AgentRepository,
            AuditRepository,
            ExecutionRepository,
            MetricsRepository,
            PluginRepository,
            WorkflowRepository,
        )
        from ghostflow.plugins.buildnext.storage.repositories.idea_repository import IdeaRepository
        from ghostflow.plugins.buildnext.storage.repositories.memory_repository import (
            MemoryRepository,
        )
        from ghostflow.plugins.buildnext.storage.repositories.user_profile_repository import (
            UserProfileRepository,
        )

        self._ideas = IdeaRepository(self._manager)
        self._user_profiles = UserProfileRepository(self._manager)
        self._memory = MemoryRepository(self._manager)
        self._plugins = PluginRepository(self._manager)
        self._agents = AgentRepository(self._manager)
        self._metrics = MetricsRepository(self._manager)
        self._workflows = WorkflowRepository(self._manager)
        self._executions = ExecutionRepository(self._manager)
        self._audit_facade = AuditRepository(self._manager)

        self._initialized = True
        self._write_audit("system", "database_initialized", details={"migrations_applied": applied})
        logger.info("StorageService initialized. Migrations applied: %s", applied)

    def close(self) -> None:
        self._manager.close()
        self._initialized = False

    # ── Observer Layer sink ────────────────────────────────────────────────────

    def ingest_event(self, activity_event: Any) -> None:
        """Accept an ActivityEvent from the Observer Layer and persist it."""
        self._ensure_ready()
        stored = StoredEvent.from_domain(activity_event)
        self._events.insert_event(stored)  # type: ignore[union-attr]
        self._write_audit(
            actor="observer",
            action="event_ingested",
            resource_type="event",
            resource_id=stored.event_id,
        )

    def ingest_session(self, session: Any) -> None:
        """Accept an ObservationSession from the Observer Layer and persist it."""
        self._ensure_ready()
        stored = StoredSession.from_domain(session)
        self._sessions.upsert_session(stored)  # type: ignore[union-attr]
        self._write_audit(
            actor="observer",
            action="session_ingested",
            resource_type="session",
            resource_id=stored.session_id,
        )

    # ── Query API ─────────────────────────────────────────────────────────────

    def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        self._ensure_ready()
        return [e.to_dict() for e in self._events.list_events(limit=limit)]  # type: ignore[union-attr]

    def get_session_events(self, session_id: str) -> list[dict[str, Any]]:
        self._ensure_ready()
        return [e.to_dict() for e in self._events.list_events_by_session(session_id)]  # type: ignore[union-attr]

    def filter_events(self, **kwargs: Any) -> list[dict[str, Any]]:
        self._ensure_ready()
        return [e.to_dict() for e in self._events.filter_events(**kwargs)]  # type: ignore[union-attr]

    # ── Health & status ───────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        if not self._initialized:
            return {"status": "not_initialized"}
        try:
            event_count = self._events.count_events()  # type: ignore[union-attr]
            session_count = self._sessions.count_sessions()  # type: ignore[union-attr]
            migrations = self._migrations.list_applied()
            return {
                "status": "ok",
                "event_count": event_count,
                "session_count": session_count,
                "migrations_applied": len(migrations),
                "db_path": str(self._manager._db_path),
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    # ── Repository accessors (for future layers) ──────────────────────────────

    @property
    def manager(self) -> SQLiteManager:
        """Expose the underlying SQLiteManager so other services can share the DB connection."""
        return self._manager

    @property
    def events(self) -> EventRepository:
        self._ensure_ready()
        return self._events  # type: ignore[return-value]

    @property
    def sessions(self) -> SessionRepository:
        self._ensure_ready()
        return self._sessions  # type: ignore[return-value]

    @property
    def candidates(self) -> WorkflowCandidateRepository:
        self._ensure_ready()
        return self._candidates  # type: ignore[return-value]

    @property
    def blueprints(self) -> BlueprintRepository:
        self._ensure_ready()
        return self._blueprints  # type: ignore[return-value]

    @property
    def audit(self) -> AuditLogRepository:
        self._ensure_ready()
        return self._audit  # type: ignore[return-value]

    @property
    def policies(self) -> PolicyRepository:
        self._ensure_ready()
        return self._policies  # type: ignore[return-value]

    @property
    def agent_executions(self) -> AgentExecutionRepository:
        self._ensure_ready()
        return self._agent_executions  # type: ignore[return-value]

    @property
    def workflow_definitions(self) -> WorkflowDefinitionRepository:
        self._ensure_ready()
        return self._workflow_definitions  # type: ignore[return-value]

    @property
    def workflow_executions(self) -> WorkflowExecutionRepository:
        self._ensure_ready()
        return self._workflow_executions  # type: ignore[return-value]

    @property
    def ideas(self) -> Any:
        self._ensure_ready()
        return self._ideas

    @property
    def user_profiles(self) -> Any:
        self._ensure_ready()
        return self._user_profiles

    @property
    def memory(self) -> Any:
        self._ensure_ready()
        return self._memory

    @property
    def plugins(self) -> Any:
        self._ensure_ready()
        return self._plugins

    @property
    def agents(self) -> Any:
        self._ensure_ready()
        return self._agents

    @property
    def metrics(self) -> Any:
        self._ensure_ready()
        return self._metrics

    @property
    def workflows(self) -> Any:
        self._ensure_ready()
        return self._workflows

    @property
    def executions(self) -> Any:
        self._ensure_ready()
        return self._executions

    @property
    def audit_records(self) -> Any:
        self._ensure_ready()
        return self._audit_facade

    # ── Internal ───────────────────────────────────────────────────────────────

    def _ensure_ready(self) -> None:
        if not self._initialized:
            raise RuntimeError("Call initialize() before using StorageService")

    def _write_audit(
        self,
        actor: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if self._audit is None:
            return
        try:
            log = AuditLog.create(
                actor=actor,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
            )
            self._audit.insert_audit_log(log)
        except Exception as exc:
            logger.warning("Audit log write failed: %s", exc)
