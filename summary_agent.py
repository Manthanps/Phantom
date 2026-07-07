"""SummaryAgent — generates workflow, execution, and productivity summaries."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ghostflow.ai.ollama.ollama_client import OllamaClient, OllamaUnavailableError
from ghostflow.ai.ollama.prompt_manager import PromptManager

if TYPE_CHECKING:
    from ghostflow.execution.models.execution_record import ExecutionRecord
    from ghostflow.pattern_discovery.models.workflow_candidate import WorkflowCandidate

logger = logging.getLogger("ghostflow.ai.summary")


@dataclass
class WorkflowSummaryReport:
    workflow_id: str
    workflow_name: str
    summary: str
    value_proposition: str
    estimated_weekly_hours_saved: float
    recommended_next_step: str
    model_used: str
    ai_generated: bool
    generated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "summary": self.summary,
            "value_proposition": self.value_proposition,
            "estimated_weekly_hours_saved": self.estimated_weekly_hours_saved,
            "recommended_next_step": self.recommended_next_step,
            "model_used": self.model_used,
            "ai_generated": self.ai_generated,
            "generated_at": self.generated_at,
        }


@dataclass
class ProductivityReport:
    period: str
    total_workflows_discovered: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    total_time_saved_seconds: float
    top_workflow_name: str
    narrative: str
    model_used: str
    ai_generated: bool
    generated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "total_workflows_discovered": self.total_workflows_discovered,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "total_time_saved_seconds": self.total_time_saved_seconds,
            "top_workflow_name": self.top_workflow_name,
            "narrative": self.narrative,
            "model_used": self.model_used,
            "ai_generated": self.ai_generated,
            "generated_at": self.generated_at,
        }


class SummaryAgent:
    def __init__(self, client: OllamaClient, model: str = "llama3.2:3b") -> None:
        self._client = client
        self._model = model

    # ── Workflow summary ───────────────────────────────────────────────────────

    async def summarize_workflow(self, candidate: WorkflowCandidate) -> WorkflowSummaryReport:
        try:
            available = await self._client.is_available()
            if not available:
                raise OllamaUnavailableError("Ollama not available")

            system, user = PromptManager.workflow_summary(
                workflow_name=candidate.name or "Unknown Workflow",
                event_sequence=candidate.sequence,
                confidence=candidate.confidence,
                frequency=candidate.frequency,
                automation_value_score=candidate.automation_value_score,
            )
            data = await self._client.generate_json(user, model=self._model, system=system)

            return WorkflowSummaryReport(
                workflow_id=candidate.candidate_id,
                workflow_name=candidate.name or "Unknown Workflow",
                summary=data.get("summary", ""),
                value_proposition=data.get("value_proposition", ""),
                estimated_weekly_hours_saved=float(data.get("estimated_weekly_hours_saved", 0)),
                recommended_next_step=data.get("recommended_next_step", ""),
                model_used=self._model,
                ai_generated=True,
            )

        except (OllamaUnavailableError, Exception) as exc:
            logger.info("Summary agent fallback: %s", exc)
            return self._fallback_workflow_summary(candidate)

    # ── Productivity report ────────────────────────────────────────────────────

    async def generate_productivity_report(
        self,
        candidates: list[WorkflowCandidate],
        executions: list[ExecutionRecord],
        period: str = "this week",
    ) -> ProductivityReport:

        successful = sum(1 for e in executions if e.success)
        failed = len(executions) - successful
        total_savings = sum(c.estimated_time_saved_per_week_hours * 3600 for c in candidates)
        top = max(candidates, key=lambda c: c.rank_score) if candidates else None

        narrative = self._build_narrative(candidates, executions, successful, failed, period)

        return ProductivityReport(
            period=period,
            total_workflows_discovered=len(candidates),
            total_executions=len(executions),
            successful_executions=successful,
            failed_executions=failed,
            total_time_saved_seconds=total_savings,
            top_workflow_name=top.name if top else "None",
            narrative=narrative,
            model_used="rule-based",
            ai_generated=False,
        )

    # ── Execution summary ──────────────────────────────────────────────────────

    def summarize_execution(self, record: ExecutionRecord) -> dict[str, Any]:
        status_label = "succeeded" if record.success else "failed"
        duration = f"{record.duration_ms / 1000:.1f}s" if record.duration_ms else "unknown"
        steps_done = record.completed_step_count

        return {
            "execution_id": record.execution_id,
            "blueprint_name": record.blueprint_name,
            "status": status_label,
            "dry_run": record.dry_run,
            "steps_completed": steps_done,
            "total_steps": len(record.step_results),
            "duration": duration,
            "rollback_performed": record.rollback_performed,
            "summary": (
                f"Blueprint '{record.blueprint_name}' {status_label} in {duration}. "
                f"{steps_done}/{len(record.step_results)} steps completed."
                + (" Rollback was performed." if record.rollback_performed else "")
            ),
        }

    # ── Fallbacks ─────────────────────────────────────────────────────────────

    @staticmethod
    def _fallback_workflow_summary(candidate: WorkflowCandidate) -> WorkflowSummaryReport:
        name = candidate.name or "Unknown Workflow"
        steps = " → ".join(candidate.sequence[:4])
        return WorkflowSummaryReport(
            workflow_id=candidate.candidate_id,
            workflow_name=name,
            summary=(
                f"'{name}' was detected {candidate.frequency} times with "
                f"{candidate.confidence:.0%} confidence. Pattern: {steps}."
            ),
            value_proposition=(
                f"Automating this could save approximately "
                f"{candidate.estimated_time_saved_per_week_hours:.1f} hours per week."
            ),
            estimated_weekly_hours_saved=candidate.estimated_time_saved_per_week_hours,
            recommended_next_step="Review the workflow graph and approve the blueprint.",
            model_used="rule-based",
            ai_generated=False,
        )

    @staticmethod
    def _build_narrative(
        candidates: list[WorkflowCandidate],
        executions: list[ExecutionRecord],
        successful: int,
        failed: int,
        period: str,
    ) -> str:
        total_savings_h = sum(c.estimated_time_saved_per_week_hours for c in candidates)
        return (
            f"GhostFlow discovered {len(candidates)} workflow pattern(s) {period}. "
            f"{len(executions)} automation(s) ran: {successful} succeeded, {failed} failed. "
            f"Total estimated weekly time savings: {total_savings_h:.1f} hours."
        )
