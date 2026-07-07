from __future__ import annotations

from typing import Any

from ghostflow.storage.models.audit_log import AuditLog
from ghostflow.storage.repositories.base_repository import BaseRepository


class AuditLogRepository(BaseRepository):
    def insert_audit_log(self, log: AuditLog) -> None:
        self.execute(
            """
            INSERT OR IGNORE INTO audit_logs
                (audit_id, timestamp, actor, action,
                 resource_type, resource_id, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            log.to_row(),
        )

    def list_audit_logs(self, limit: int = 100, offset: int = 0) -> list[AuditLog]:
        rows = self.fetch_all(
            "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [AuditLog.from_row(r) for r in rows]

    def filter_audit_logs(
        self,
        action: str | None = None,
        resource_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        clauses: list[str] = []
        params: list[Any] = []

        if action:
            clauses.append("action = ?")
            params.append(action)
        if resource_type:
            clauses.append("resource_type = ?")
            params.append(resource_type)
        if start_date:
            clauses.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("timestamp <= ?")
            params.append(end_date)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.extend([limit, offset])

        rows = self.fetch_all(
            f"SELECT * FROM audit_logs {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            tuple(params),
        )
        return [AuditLog.from_row(r) for r in rows]
