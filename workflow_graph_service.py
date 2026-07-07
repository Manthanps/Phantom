"""WorkflowGraphService — main integration point for the Workflow Graph Layer.

Usage (from Blueprint Generator or API layer)::

    from ghostflow.workflow_graph.services.workflow_graph_service import WorkflowGraphService

    service = WorkflowGraphService()

    # From Pattern Discovery output
    graph = service.build_graph_from_candidate(candidate)

    validation = service.validate_graph(graph)
    plan = service.generate_execution_plan(graph)
    metrics = service.get_graph_metrics(graph)
    mermaid = service.export_mermaid(graph)
"""

from __future__ import annotations

from typing import Any

from ghostflow.workflow_graph.analysis.dependency_analyzer import (
    DependencyAnalysisResult,
    DependencyAnalyzer,
)
from ghostflow.workflow_graph.analysis.execution_order_resolver import (
    ExecutionOrderResolver,
)
from ghostflow.workflow_graph.analysis.graph_metrics_engine import GraphMetricsEngine
from ghostflow.workflow_graph.analysis.graph_validator import (
    GraphValidationResult,
    GraphValidator,
)
from ghostflow.workflow_graph.builders.dag_generator import DAGGenerationResult, DAGGenerator
from ghostflow.workflow_graph.builders.graph_builder import GraphBuilder
from ghostflow.workflow_graph.models.execution_plan import ExecutionPlan
from ghostflow.workflow_graph.models.graph_metrics import WorkflowGraphMetrics
from ghostflow.workflow_graph.models.workflow_graph import WorkflowGraph
from ghostflow.workflow_graph.serialization.graph_exporter import GraphExporter
from ghostflow.workflow_graph.serialization.graph_serializer import GraphSerializer


class WorkflowGraphService:
    """Orchestrates the full WorkflowCandidate → WorkflowGraph pipeline.

    All components are instantiated once and reused across calls (stateless).
    """

    def __init__(self) -> None:
        self._builder = GraphBuilder()
        self._dag_gen = DAGGenerator()
        self._dep_analyzer = DependencyAnalyzer()
        self._order_resolver = ExecutionOrderResolver()
        self._validator = GraphValidator()
        self._metrics_engine = GraphMetricsEngine()

    # ── Primary API ───────────────────────────────────────────────────────────

    def build_graph_from_candidate(self, candidate: Any) -> WorkflowGraph:
        """Convert a WorkflowCandidate (or any compatible object) into a WorkflowGraph."""
        return self._builder.build(candidate)

    def validate_graph(self, graph: WorkflowGraph) -> GraphValidationResult:
        return self._validator.validate(graph)

    def analyze_dependencies(self, graph: WorkflowGraph) -> DependencyAnalysisResult:
        return self._dep_analyzer.analyze(graph)

    def generate_execution_plan(self, graph: WorkflowGraph) -> ExecutionPlan:
        return self._order_resolver.resolve(graph)

    def get_graph_metrics(self, graph: WorkflowGraph) -> WorkflowGraphMetrics:
        return self._metrics_engine.compute(graph)

    # ── Serialization ─────────────────────────────────────────────────────────

    def serialize_graph(self, graph: WorkflowGraph) -> dict[str, Any]:
        return GraphSerializer.to_dict(graph)

    def export_mermaid(self, graph: WorkflowGraph) -> str:
        return GraphExporter.to_mermaid(graph)

    def export_dot(self, graph: WorkflowGraph) -> str:
        return GraphExporter.to_dot(graph)

    # ── DAG analysis ──────────────────────────────────────────────────────────

    def generate_dag(self, graph: WorkflowGraph) -> DAGGenerationResult:
        return self._dag_gen.generate(graph)

    # ── Full pipeline ─────────────────────────────────────────────────────────

    def full_pipeline(self, candidate: Any) -> dict[str, Any]:
        """Single call: candidate → graph + all analyses + metrics.

        Returns a dict with keys:
            graph, validation, dependencies, execution_plan, metrics, dag_result
        """
        graph = self.build_graph_from_candidate(candidate)
        return {
            "graph": graph,
            "validation": self.validate_graph(graph),
            "dependencies": self.analyze_dependencies(graph),
            "execution_plan": self.generate_execution_plan(graph),
            "metrics": self.get_graph_metrics(graph),
            "dag_result": self.generate_dag(graph),
        }
