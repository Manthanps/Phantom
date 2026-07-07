"""ExceptionRuleRepository — persistence for exception_rules table."""

from __future__ import annotations

from datetime import UTC, datetime

from ghostflow.exception_learning.models.exception_rule import ExceptionRule
from ghostflow.storage.repositories.base_repository import BaseRepository


class ExceptionRuleRepository(BaseRepository):
    """CRUD for the exception_rules table."""

    def upsert(self, rule: ExceptionRule) -> None:
        """Insert a new rule or reinforce (bump count + confidence) if it already exists."""
        existing = self.get_by_workflow_pattern_type(
            rule.workflow_id, rule.pattern, rule.rule_type.value
        )
        if existing is None:
            self._insert(rule)
        else:
            self._reinforce(
                existing.rule_id,
                rule.rejection_count,
                rule.confidence,
                rule.last_rejection_at,
            )

    def _insert(self, rule: ExceptionRule) -> None:
        row = rule.to_row()
        with self._manager.transaction() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO exception_rules
                    (rule_id, workflow_id, pattern, rule_type, match_strategy, confidence,
                     rejection_count, rationale, is_active, last_rejection_at, created_at, updated_at)
                VALUES
                    (:rule_id, :workflow_id, :pattern, :rule_type, :match_strategy, :confidence,
                     :rejection_count, :rationale, :is_active, :last_rejection_at, :created_at, :updated_at)
                """,
                row,
            )

    def _reinforce(
        self,
        rule_id: str,
        extra_count: int,
        new_confidence: float,
        last_rejection_at: str,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        self.execute(
            """
            UPDATE exception_rules
            SET rejection_count    = rejection_count + ?,
                confidence         = MAX(confidence, ?),
                last_rejection_at  = ?,
                updated_at         = ?
            WHERE rule_id = ?
            """,
            (extra_count, new_confidence, last_rejection_at, now, rule_id),
        )

    def get_by_id(self, rule_id: str) -> ExceptionRule | None:
        row = self.fetch_one("SELECT * FROM exception_rules WHERE rule_id = ?", (rule_id,))
        return ExceptionRule.from_row(row) if row else None

    def get_by_workflow_pattern_type(
        self, workflow_id: str, pattern: str, rule_type: str
    ) -> ExceptionRule | None:
        row = self.fetch_one(
            "SELECT * FROM exception_rules WHERE workflow_id = ? AND pattern = ? AND rule_type = ?",
            (workflow_id, pattern, rule_type),
        )
        return ExceptionRule.from_row(row) if row else None

    def list_active_by_workflow(self, workflow_id: str) -> list[ExceptionRule]:
        rows = self.fetch_all(
            """
            SELECT * FROM exception_rules
            WHERE (workflow_id = ? OR workflow_id = '') AND is_active = 1
            ORDER BY confidence DESC
            """,
            (workflow_id,),
        )
        return [ExceptionRule.from_row(r) for r in rows]

    def list_all_active(self) -> list[ExceptionRule]:
        rows = self.fetch_all(
            "SELECT * FROM exception_rules WHERE is_active = 1 ORDER BY confidence DESC"
        )
        return [ExceptionRule.from_row(r) for r in rows]

    def deactivate(self, rule_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        self.execute(
            "UPDATE exception_rules SET is_active = 0, updated_at = ? WHERE rule_id = ?",
            (now, rule_id),
        )

    def count_active(self, workflow_id: str = "") -> int:
        if workflow_id:
            row = self.fetch_one(
                "SELECT COUNT(*) as cnt FROM exception_rules WHERE workflow_id = ? AND is_active = 1",
                (workflow_id,),
            )
        else:
            row = self.fetch_one("SELECT COUNT(*) as cnt FROM exception_rules WHERE is_active = 1")
        return int(row["cnt"]) if row else 0
