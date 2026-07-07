"""ApprovalAgent — AI advisory assistant for blueprint approval decisions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ghostflow.ai.models.approval_recommendation import ApprovalDecision, ApprovalRecommendation
from ghostflow.ai.ollama.ollama_client import OllamaClient, OllamaUnavailableError
from ghostflow.ai.ollama.prompt_manager import PromptManager

if TYPE_CHECKING:
    from ghostflow.blueprints.models.blueprint import WorkflowBlueprint
    from ghostflow.blueprints.validation.blueprint_validator import BlueprintValidationResult

logger = logging.getLogger("ghostflow.ai.approval")


class ApprovalAgent:
    """
    Advisory AI approval assistant.

    IMPORTANT: This agent's recommendation is advisory only. The Safety Layer
    has final authority. This agent cannot approve or reject a blueprint on
    behalf of the system — only a human can approve execution.
    """

    def __init__(self, client: OllamaClient, model: str = "llama3.2:3b") -> None:
        self._client = client
        self._model = model

    async def run(
        self,
        blueprint: WorkflowBlueprint,
        validation_result: BlueprintValidationResult | None = None,
    ) -> ApprovalRecommendation:
        action_types = [a.action_type.value for a in blueprint.actions]
        errors = validation_result.errors if validation_result else []
        warnings = validation_result.warnings if validation_result else []
        has_rollback = blueprint.rollback_plan is not None

        try:
            available = await self._client.is_available()
            if not available:
                raise OllamaUnavailableError("Ollama not available")

            system, user = PromptManager.approval(
                blueprint_name=blueprint.name,
                action_types=action_types,
                action_count=len(blueprint.actions),
                validation_errors=errors,
                validation_warnings=warnings,
                has_rollback_plan=has_rollback,
                confidence_score=blueprint.confidence_score,
            )
            data = await self._client.generate_json(user, model=self._model, system=system)

            decision_str = data.get("decision", "defer").lower()
            try:
                decision = ApprovalDecision(decision_str)
            except ValueError:
                decision = ApprovalDecision.DEFER

            return ApprovalRecommendation(
                blueprint_id=blueprint.blueprint_id,
                blueprint_name=blueprint.name,
                decision=decision,
                explanation=data.get("explanation", ""),
                risk_summary=data.get("risk_summary", ""),
                concerns=data.get("concerns", []),
                positive_factors=data.get("positive_factors", []),
                confidence=float(data.get("confidence", 0.7)),
                model_used=self._model,
                ai_generated=True,
            )

        except (OllamaUnavailableError, Exception) as exc:
            logger.info("Approval agent fallback: %s", exc)
            return self._fallback(blueprint, action_types, errors, warnings, has_rollback)

    # ── Fallback ──────────────────────────────────────────────────────────────

    def _fallback(
        self,
        blueprint: WorkflowBlueprint,
        action_types: list[str],
        errors: list[str],
        warnings: list[str],
        has_rollback: bool,
    ) -> ApprovalRecommendation:
        concerns: list[str] = list(errors) + list(warnings)
        positives: list[str] = []

        if errors:
            decision = ApprovalDecision.REJECT
            explanation = f"Blueprint has {len(errors)} validation error(s) that must be resolved."
        elif any("delete" in at for at in action_types):
            decision = ApprovalDecision.APPROVE_WITH_WARNING
            explanation = (
                "Blueprint contains file deletion steps. Review carefully before approving."
            )
            concerns.append("Contains destructive file operations.")
        elif has_rollback and blueprint.confidence_score >= 0.7:
            decision = ApprovalDecision.APPROVE
            explanation = "Blueprint has a rollback plan and high confidence. Safe to approve."
            positives.append(f"Confidence score: {blueprint.confidence_score:.0%}")
            positives.append("Rollback plan present.")
        else:
            decision = ApprovalDecision.APPROVE_WITH_WARNING
            explanation = "Review recommended before approving."
            if not has_rollback:
                concerns.append("No rollback plan.")

        return ApprovalRecommendation(
            blueprint_id=blueprint.blueprint_id,
            blueprint_name=blueprint.name,
            decision=decision,
            explanation=explanation,
            risk_summary=self._risk_summary(action_types),
            concerns=concerns,
            positive_factors=positives,
            confidence=0.6,
            model_used="rule-based",
            ai_generated=False,
        )

    @staticmethod
    def _risk_summary(action_types: list[str]) -> str:
        has_delete = any("delete" in at for at in action_types)
        has_command = any("command" in at for at in action_types)
        if has_delete and has_command:
            return "High risk: contains destructive and command execution steps."
        if has_delete:
            return "Medium-high risk: contains file deletion steps."
        if has_command:
            return "Medium risk: contains command execution steps."
        return "Low risk: read-only file organization operations."
