"""WorkflowExplanationAgent — generates plain-language workflow explanations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ghostflow.ai.models.workflow_summary import WorkflowSummary
from ghostflow.ai.ollama.ollama_client import OllamaClient, OllamaUnavailableError
from ghostflow.ai.ollama.prompt_manager import PromptManager

if TYPE_CHECKING:
    from ghostflow.blueprints.models.blueprint import WorkflowBlueprint
    from ghostflow.workflow_graph.models.workflow_graph import WorkflowGraph

logger = logging.getLogger("ghostflow.ai.explanation")


class WorkflowExplanationAgent:
    """
    Produces a human-readable explanation of a workflow combining graph + blueprint context.
    """

    def __init__(self, client: OllamaClient, model: str = "llama3.2:3b") -> None:
        self._client = client
        self._model = model

    async def run(
        self,
        graph: WorkflowGraph,
        blueprint: WorkflowBlueprint | None = None,
    ) -> WorkflowSummary:
        event_sequence = [n.event_type for n in graph.nodes]
        action_descriptions = (
            [a.parameters.get("description", a.action_type.value) for a in blueprint.actions]
            if blueprint
            else []
        )
        step_count = len(blueprint.actions) if blueprint else len(graph.nodes)

        try:
            available = await self._client.is_available()
            if not available:
                raise OllamaUnavailableError("Ollama not available")

            system, user = PromptManager.workflow_explanation(
                graph.name, event_sequence, action_descriptions, step_count
            )
            data = await self._client.generate_json(user, model=self._model, system=system)

            return WorkflowSummary(
                workflow_id=graph.graph_id,
                name=graph.name,
                short_title=graph.name,
                category="",
                description=data.get("description") or self._fallback_description(graph),
                key_steps=data.get("key_steps") or event_sequence,
                estimated_duration_seconds=float(data.get("estimated_duration_seconds", 0)),
                automation_value=data.get("automation_value") or "medium",
                confidence=float(data.get("confidence", 0.7)),
                model_used=self._model,
                ai_generated=True,
            )

        except (OllamaUnavailableError, Exception) as exc:
            logger.info("Explanation agent fallback: %s", exc)
            return self._fallback(graph, event_sequence)

    def _fallback(self, graph: WorkflowGraph, event_sequence: list[str]) -> WorkflowSummary:
        return WorkflowSummary(
            workflow_id=graph.graph_id,
            name=graph.name,
            short_title=graph.name,
            category="",
            description=self._fallback_description(graph),
            key_steps=event_sequence,
            estimated_duration_seconds=len(event_sequence) * 5.0,
            automation_value="medium",
            confidence=graph.confidence,
            model_used="rule-based",
            ai_generated=False,
        )

    @staticmethod
    def _fallback_description(graph: WorkflowGraph) -> str:
        steps = " → ".join(n.event_type.replace("_", " ") for n in graph.nodes[:4])
        suffix = "…" if len(graph.nodes) > 4 else ""
        return (
            f"This workflow performs {len(graph.nodes)} steps: {steps}{suffix}. "
            f"It was observed with {graph.confidence:.0%} confidence across multiple sessions."
        )
