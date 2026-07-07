"""IncidentAnalysisAgent — diagnoses execution failures with AI or rule-based fallback."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ghostflow.ai.models.incident_analysis import IncidentAnalysis
from ghostflow.ai.ollama.ollama_client import OllamaClient, OllamaUnavailableError
from ghostflow.ai.ollama.prompt_manager import PromptManager

if TYPE_CHECKING:
    from ghostflow.execution.models.execution_record import ExecutionRecord
    from ghostflow.execution.models.incident_report import IncidentReport

logger = logging.getLogger("ghostflow.ai.incident")

# Common error patterns and their human-readable diagnoses
_ERROR_PATTERNS: dict[str, tuple[str, str]] = {
    "FileNotFoundError": (
        "The source file did not exist at execution time.",
        "The file may have been moved, renamed, or deleted by another process before this step ran.",
    ),
    "PermissionError": (
        "Insufficient permissions to access the file or directory.",
        "The workflow requires elevated privileges for this operation.",
    ),
    "TimeoutError": (
        "The operation exceeded its configured timeout.",
        "The command or file operation took longer than expected.",
    ),
    "allowlist": (
        "A command was blocked by the GhostFlow security allowlist.",
        "The workflow attempted to run a command not permitted by GhostFlow policy.",
    ),
    "circular": (
        "A circular dependency was detected in the workflow action graph.",
        "Two or more steps depend on each other, creating a deadlock.",
    ),
}


class IncidentAnalysisAgent:
    """
    Analyzes an IncidentReport and produces a human-readable IncidentAnalysis.
    """

    def __init__(self, client: OllamaClient, model: str = "llama3.2:3b") -> None:
        self._client = client
        self._model = model

    async def run(
        self,
        incident: IncidentReport,
        execution: ExecutionRecord | None = None,
    ) -> IncidentAnalysis:
        blueprint_name = execution.blueprint_name if execution else "Unknown Workflow"
        rollback_performed = execution.rollback_performed if execution else False

        try:
            available = await self._client.is_available()
            if not available:
                raise OllamaUnavailableError("Ollama not available")

            system, user = PromptManager.incident_analysis(
                failed_step_id=incident.failed_step_id,
                error_message=incident.error_message,
                completed_steps=incident.completed_step_ids,
                blueprint_name=blueprint_name,
                rollback_performed=rollback_performed,
            )
            data = await self._client.generate_json(user, model=self._model, system=system)

            return IncidentAnalysis(
                incident_id=incident.incident_id,
                execution_id=incident.execution_id,
                root_cause=data.get("root_cause") or incident.error_message,
                probable_cause=data.get("probable_cause") or incident.error_message,
                contributing_factors=data.get("contributing_factors", []),
                recovery_suggestions=data.get("recovery_suggestions", []),
                prevention_recommendations=data.get("prevention_recommendations", []),
                severity=data.get("severity") or self._infer_severity(incident),
                model_used=self._model,
                ai_generated=True,
            )

        except (OllamaUnavailableError, Exception) as exc:
            logger.info("Incident analysis fallback: %s", exc)
            return self._fallback(incident, blueprint_name, rollback_performed)

    # ── Fallback ──────────────────────────────────────────────────────────────

    def _fallback(
        self,
        incident: IncidentReport,
        blueprint_name: str,
        rollback_performed: bool,
    ) -> IncidentAnalysis:
        root_cause, probable_cause = self._pattern_match(incident.error_message)
        recovery = self._recovery_suggestions(incident, rollback_performed)

        return IncidentAnalysis(
            incident_id=incident.incident_id,
            execution_id=incident.execution_id,
            root_cause=root_cause,
            probable_cause=probable_cause,
            contributing_factors=self._contributing_factors(incident),
            recovery_suggestions=recovery,
            prevention_recommendations=self._prevention(incident),
            severity=self._infer_severity(incident),
            model_used="rule-based",
            ai_generated=False,
        )

    @staticmethod
    def _pattern_match(error: str) -> tuple[str, str]:
        for keyword, (root, probable) in _ERROR_PATTERNS.items():
            if keyword.lower() in error.lower():
                return root, probable
        return error, "An unexpected error occurred during step execution."

    @staticmethod
    def _infer_severity(incident: IncidentReport) -> str:
        error = incident.error_message.lower()
        if "permission" in error or "circular" in error:
            return "high"
        if "timeout" in error or "command" in error:
            return "medium"
        return "low"

    @staticmethod
    def _recovery_suggestions(incident: IncidentReport, rollback_performed: bool) -> list[str]:
        suggestions = []
        if rollback_performed:
            suggestions.append("Rollback was performed — previous steps have been undone.")
        else:
            suggestions.append("Check the state of files modified before the failure.")
        suggestions.append(f"Review the failed step: {incident.failed_step_id}")
        suggestions.append("Verify file paths and permissions before re-running.")
        return suggestions

    @staticmethod
    def _contributing_factors(incident: IncidentReport) -> list[str]:
        factors = []
        if incident.completed_step_ids:
            factors.append(f"{len(incident.completed_step_ids)} steps completed before failure.")
        if "FileNotFoundError" in incident.error_message:
            factors.append("File system state changed between observation and execution.")
        return factors

    @staticmethod
    def _prevention(incident: IncidentReport) -> list[str]:
        return [
            "Add a pre-condition check to verify source files exist before moving them.",
            "Increase timeout values for operations on slow storage.",
            "Use dry-run mode to validate blueprint before live execution.",
        ]
