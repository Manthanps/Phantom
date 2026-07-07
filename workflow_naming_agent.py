"""WorkflowNamingAgent — generates human-readable workflow names from event sequences."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ghostflow.ai.models.workflow_summary import WorkflowSummary
from ghostflow.ai.ollama.ollama_client import OllamaClient, OllamaUnavailableError
from ghostflow.ai.ollama.prompt_manager import PromptManager

if TYPE_CHECKING:
    from ghostflow.workflow_graph.models.workflow_graph import WorkflowGraph

logger = logging.getLogger("ghostflow.ai.naming")

# Category keywords used for rule-based fallback
_CATEGORY_MAP: dict[str, str] = {
    "file_created": "File Creation",
    "file_modified": "Document Processing",
    "file_moved": "File Organization",
    "file_deleted": "File Cleanup",
    "folder_created": "Directory Management",
    "folder_moved": "Directory Organization",
    "folder_deleted": "Directory Cleanup",
}


class WorkflowNamingAgent:
    """
    Generates a name, title, and category for a WorkflowGraph.

    Falls back to rule-based naming when Ollama is unavailable.
    """

    def __init__(self, client: OllamaClient, model: str = "llama3.2:3b") -> None:
        self._client = client
        self._model = model
        self._prompts = PromptManager()

    async def run(self, graph: WorkflowGraph) -> WorkflowSummary:
        event_sequence = [n.event_type for n in graph.nodes]
        candidate_name = graph.name or ""
        classification = graph.metadata.get("classification", "")

        try:
            available = await self._client.is_available()
            if not available:
                raise OllamaUnavailableError("Ollama not available")

            system, user = PromptManager.workflow_naming(
                event_sequence, candidate_name, classification
            )
            data = await self._client.generate_json(user, model=self._model, system=system)

            return WorkflowSummary(
                workflow_id=graph.graph_id,
                name=data.get("name") or self._fallback_name(event_sequence),
                short_title=data.get("short_title") or candidate_name,
                category=data.get("category") or self._fallback_category(event_sequence),
                description=data.get("confidence_explanation") or "",
                key_steps=event_sequence,
                estimated_duration_seconds=0.0,
                automation_value="medium",
                confidence=float(data.get("confidence", 0.7)),
                model_used=self._model,
                ai_generated=True,
            )

        except (OllamaUnavailableError, Exception) as exc:
            logger.info("Falling back to rule-based naming: %s", exc)
            return self._fallback_summary(graph, event_sequence)

    # ── Fallback (rule-based) ─────────────────────────────────────────────────

    def _fallback_summary(self, graph: WorkflowGraph, event_sequence: list[str]) -> WorkflowSummary:
        return WorkflowSummary(
            workflow_id=graph.graph_id,
            name=self._fallback_name(event_sequence),
            short_title=graph.name or "Unnamed Workflow",
            category=self._fallback_category(event_sequence),
            description=f"Workflow with {len(event_sequence)} steps: {' → '.join(event_sequence[:3])}",
            key_steps=event_sequence,
            estimated_duration_seconds=len(event_sequence) * 5.0,
            automation_value=self._infer_value(graph),
            confidence=graph.confidence,
            model_used="rule-based",
            ai_generated=False,
        )

    @staticmethod
    def _fallback_name(event_sequence: list[str]) -> str:
        if not event_sequence:
            return "Unknown Workflow"
        # Build name from dominant event types
        first = event_sequence[0].replace("_", " ").title()
        last = event_sequence[-1].replace("_", " ").title()
        if first == last:
            return f"{first} Workflow"
        return f"{first} to {last} Workflow"

    @staticmethod
    def _fallback_category(event_sequence: list[str]) -> str:
        for event in event_sequence:
            for key, category in _CATEGORY_MAP.items():
                if key in event:
                    return category
        return "General Automation"

    @staticmethod
    def _infer_value(graph: WorkflowGraph) -> str:
        if graph.confidence >= 0.8 and len(graph.nodes) >= 3:
            return "high"
        if graph.confidence >= 0.5:
            return "medium"
        return "low"
