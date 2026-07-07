"""RecommendationAgent — ranks workflows by automation priority."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ghostflow.ai.models.recommendation import RecommendationList, WorkflowRecommendation
from ghostflow.ai.ollama.ollama_client import OllamaClient, OllamaUnavailableError
from ghostflow.ai.ollama.prompt_manager import PromptManager

if TYPE_CHECKING:
    from ghostflow.pattern_discovery.models.workflow_candidate import WorkflowCandidate

logger = logging.getLogger("ghostflow.ai.recommendation")


class RecommendationAgent:
    """
    Produces a prioritized list of automation recommendations from WorkflowCandidates.

    Scoring formula (rule-based fallback):
        priority = 0.4 * confidence + 0.3 * normalized_frequency + 0.3 * automation_value
    """

    def __init__(self, client: OllamaClient, model: str = "llama3.2:3b") -> None:
        self._client = client
        self._model = model

    async def run(self, candidates: list[WorkflowCandidate]) -> RecommendationList:
        if not candidates:
            return RecommendationList(
                recommendations=[], total_estimated_weekly_savings_seconds=0.0, model_used="none"
            )

        candidate_dicts = [
            {
                "id": c.candidate_id,
                "name": c.name or c.sequence[0] if c.sequence else "unknown",
                "confidence": c.confidence,
                "frequency": c.frequency,
                "step_count": len(c.sequence),
                "automation_value_score": c.automation_value_score,
            }
            for c in candidates
        ]

        try:
            available = await self._client.is_available()
            if not available:
                raise OllamaUnavailableError("Ollama not available")

            system, user = PromptManager.recommendation(candidate_dicts)
            data = await self._client.generate_json(user, model=self._model, system=system)

            id_to_candidate = {c.candidate_id: c for c in candidates}
            recs: list[WorkflowRecommendation] = []

            for item in data.get("rankings", []):
                wf_id = item.get("workflow_id", "")
                cand = id_to_candidate.get(wf_id)
                recs.append(
                    WorkflowRecommendation(
                        workflow_id=wf_id,
                        workflow_name=cand.name if cand else wf_id,
                        priority_rank=int(item.get("priority_rank", 99)),
                        priority_score=float(item.get("priority_score", 0.5)),
                        reasoning=item.get("reasoning", ""),
                        frequency_factor=cand.support if cand else 0.0,
                        confidence_factor=cand.confidence if cand else 0.0,
                        complexity_factor=1.0 - min(1.0, len(cand.sequence) / 10.0)
                        if cand
                        else 0.5,
                        risk_factor=self._estimate_risk(cand),
                        estimated_time_savings_per_week_seconds=float(
                            item.get("estimated_time_savings_per_week_seconds", 0)
                        ),
                        recommended_action=item.get("recommended_action", "review_first"),
                        model_used=self._model,
                        ai_generated=True,
                    )
                )

            recs.sort(key=lambda r: r.priority_rank)
            total_savings = float(data.get("total_estimated_weekly_savings_seconds", 0))

            return RecommendationList(
                recommendations=recs,
                total_estimated_weekly_savings_seconds=total_savings,
                model_used=self._model,
                ai_generated=True,
            )

        except (OllamaUnavailableError, Exception) as exc:
            logger.info("Recommendation agent fallback: %s", exc)
            return self._fallback(candidates)

    # ── Fallback ──────────────────────────────────────────────────────────────

    def _fallback(self, candidates: list[WorkflowCandidate]) -> RecommendationList:
        max_freq = max((c.frequency for c in candidates), default=1) or 1
        scored = sorted(
            candidates,
            key=lambda c: (
                0.4 * c.confidence
                + 0.3 * (c.frequency / max_freq)
                + 0.3 * min(1.0, c.automation_value_score / 10.0)
            ),
            reverse=True,
        )

        recs = [
            WorkflowRecommendation(
                workflow_id=c.candidate_id,
                workflow_name=c.name or f"Workflow-{i + 1}",
                priority_rank=i + 1,
                priority_score=round(
                    0.4 * c.confidence
                    + 0.3 * (c.frequency / max_freq)
                    + 0.3 * min(1.0, c.automation_value_score / 10.0),
                    3,
                ),
                reasoning=self._fallback_reasoning(c),
                frequency_factor=c.support,
                confidence_factor=c.confidence,
                complexity_factor=1.0 - min(1.0, len(c.sequence) / 10.0),
                risk_factor=self._estimate_risk(c),
                estimated_time_savings_per_week_seconds=c.estimated_time_saved_per_week_hours
                * 3600,
                recommended_action=self._recommended_action(c),
                model_used="rule-based",
                ai_generated=False,
            )
            for i, c in enumerate(scored)
        ]

        total = sum(r.estimated_time_savings_per_week_seconds for r in recs)
        return RecommendationList(
            recommendations=recs,
            total_estimated_weekly_savings_seconds=total,
            model_used="rule-based",
        )

    @staticmethod
    def _estimate_risk(candidate: WorkflowCandidate | None) -> float:
        if candidate is None:
            return 0.5
        has_delete = any("delete" in e for e in candidate.sequence)
        has_move = any("move" in e for e in candidate.sequence)
        base = 0.2
        if has_delete:
            base += 0.4
        if has_move:
            base += 0.2
        return min(1.0, base)

    @staticmethod
    def _recommended_action(c: WorkflowCandidate) -> str:
        if c.confidence >= 0.8 and not any("delete" in e for e in c.sequence):
            return "automate_immediately"
        if c.confidence >= 0.6:
            return "review_first"
        return "monitor"

    @staticmethod
    def _fallback_reasoning(c: WorkflowCandidate) -> str:
        return (
            f"Detected {c.frequency} times with {c.confidence:.0%} confidence. "
            f"Pattern: {' → '.join(c.sequence[:3])}{'…' if len(c.sequence) > 3 else ''}."
        )
