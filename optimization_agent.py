"""OptimizationAgent — detects redundancy, bottlenecks, and parallelization opportunities."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from ghostflow.ai.models.optimization_report import OptimizationOpportunity, OptimizationReport
from ghostflow.ai.ollama.ollama_client import OllamaClient, OllamaUnavailableError
from ghostflow.ai.ollama.prompt_manager import PromptManager

if TYPE_CHECKING:
    from ghostflow.workflow_graph.models.workflow_graph import WorkflowGraph

logger = logging.getLogger("ghostflow.ai.optimization")


class OptimizationAgent:
    """
    Analyzes a WorkflowGraph and produces an OptimizationReport.

    Rule-based heuristics run first; AI enriches with natural-language descriptions
    and catches patterns the heuristics miss.
    """

    def __init__(self, client: OllamaClient, model: str = "llama3.2:3b") -> None:
        self._client = client
        self._model = model

    async def run(self, graph: WorkflowGraph) -> OptimizationReport:
        event_sequence = [n.event_type for n in graph.nodes]
        node_count = len(graph.nodes)
        edge_count = len(graph.edges)
        complexity = graph.complexity_score

        # Always run heuristics — they work offline
        heuristic_opps = self._heuristic_analysis(graph)

        try:
            available = await self._client.is_available()
            if not available:
                raise OllamaUnavailableError("Ollama not available")

            system, user = PromptManager.optimization(
                graph.name, event_sequence, node_count, edge_count, complexity
            )
            data = await self._client.generate_json(user, model=self._model, system=system)

            ai_opps = [
                OptimizationOpportunity(
                    opportunity_id=str(uuid.uuid4()),
                    opportunity_type=o.get("type", ""),
                    description=o.get("description", ""),
                    affected_steps=o.get("affected_steps", []),
                    suggested_fix=o.get("suggested_fix", ""),
                    estimated_time_saved_seconds=float(o.get("estimated_time_saved_seconds", 0)),
                    confidence=float(o.get("confidence", 0.7)),
                )
                for o in data.get("opportunities", [])
            ]

            all_opps = self._merge(heuristic_opps, ai_opps)
            total_saved = sum(o.estimated_time_saved_seconds for o in all_opps)

            return OptimizationReport(
                workflow_id=graph.graph_id,
                workflow_name=graph.name,
                opportunities=all_opps,
                overall_assessment=data.get("overall_assessment", ""),
                total_time_saved_seconds=total_saved,
                optimization_score=float(data.get("optimization_score", 0.0)),
                model_used=self._model,
                ai_generated=True,
            )

        except (OllamaUnavailableError, Exception) as exc:
            logger.info("Optimization agent fallback: %s", exc)
            return self._fallback_report(graph, heuristic_opps)

    # ── Heuristic analysis (always runs, no LLM required) ────────────────────

    def _heuristic_analysis(self, graph: WorkflowGraph) -> list[OptimizationOpportunity]:
        opps: list[OptimizationOpportunity] = []
        events = [n.event_type for n in graph.nodes]

        # Detect consecutive duplicate events
        for i in range(len(events) - 1):
            if events[i] == events[i + 1]:
                opps.append(
                    OptimizationOpportunity(
                        opportunity_type="redundant_step",
                        description=f"Step '{events[i]}' appears twice in a row.",
                        affected_steps=[events[i], events[i + 1]],
                        suggested_fix="Merge or remove the duplicate step.",
                        estimated_time_saved_seconds=5.0,
                        confidence=0.9,
                    )
                )

        # Flag long linear chains with no branching as potential bottlenecks
        if len(graph.nodes) > 6 and len(graph.edges) == len(graph.nodes) - 1:
            opps.append(
                OptimizationOpportunity(
                    opportunity_type="bottleneck",
                    description=f"Workflow has {len(graph.nodes)} strictly sequential steps.",
                    affected_steps=events,
                    suggested_fix="Consider which steps can run in parallel.",
                    estimated_time_saved_seconds=float(len(graph.nodes) * 2),
                    confidence=0.6,
                )
            )

        return opps

    @staticmethod
    def _merge(
        heuristic: list[OptimizationOpportunity],
        ai: list[OptimizationOpportunity],
    ) -> list[OptimizationOpportunity]:
        """Combine heuristic and AI opportunities, deduplicating by type+description."""
        seen: set[tuple[str, str]] = set()
        merged: list[OptimizationOpportunity] = []
        for opp in heuristic + ai:
            key = (opp.opportunity_type, opp.description[:40])
            if key not in seen:
                seen.add(key)
                merged.append(opp)
        return merged

    def _fallback_report(
        self,
        graph: WorkflowGraph,
        heuristic_opps: list[OptimizationOpportunity],
    ) -> OptimizationReport:
        total = sum(o.estimated_time_saved_seconds for o in heuristic_opps)
        return OptimizationReport(
            workflow_id=graph.graph_id,
            workflow_name=graph.name,
            opportunities=heuristic_opps,
            overall_assessment=(
                f"Heuristic analysis found {len(heuristic_opps)} potential optimization(s). "
                "Run with Ollama enabled for deeper AI analysis."
            ),
            total_time_saved_seconds=total,
            optimization_score=min(1.0, total / 60.0),
            model_used="rule-based",
            ai_generated=False,
        )
