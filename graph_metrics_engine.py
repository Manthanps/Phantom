"""GraphMetricsEngine — structural and automation-readiness metrics."""

from __future__ import annotations

import networkx as nx

from ghostflow.workflow_graph.models.graph_metrics import WorkflowGraphMetrics
from ghostflow.workflow_graph.models.workflow_graph import WorkflowGraph


class GraphMetricsEngine:
    """Computes WorkflowGraphMetrics from a WorkflowGraph.

    Automation readiness (0–10) considers:
    - Average node confidence (40 %)
    - Workflow simplicity — lower complexity is easier to automate (30 %)
    - Repetition frequency — high-frequency workflows have more to gain (30 %)
    """

    def compute(self, workflow_graph: WorkflowGraph) -> WorkflowGraphMetrics:
        nx_graph = workflow_graph.to_networkx()
        n_nodes = nx_graph.number_of_nodes()
        n_edges = nx_graph.number_of_edges()

        if n_nodes == 0:
            return WorkflowGraphMetrics()

        density = round(nx.density(nx_graph), 4)

        avg_confidence = round(sum(node.confidence for node in workflow_graph.nodes) / n_nodes, 4)

        # complexity = directed density (edges / max_possible_directed_edges)
        max_edges = n_nodes * (n_nodes - 1)
        complexity_score = round(n_edges / max_edges, 4) if max_edges > 0 else 0.0

        # Average out-degree for nodes that actually branch (out_degree > 0)
        out_degrees = [d for _, d in nx_graph.out_degree() if d > 0]
        branching_factor = round(sum(out_degrees) / len(out_degrees), 4) if out_degrees else 0.0

        # Longest path: meaningful only for DAGs
        longest_path_length = 0
        if nx.is_directed_acyclic_graph(nx_graph):
            try:
                longest_path_length = len(nx.dag_longest_path(nx_graph))
            except Exception:
                longest_path_length = n_nodes

        automation_readiness = self._automation_readiness(
            workflow_graph=workflow_graph,
            is_dag=nx.is_directed_acyclic_graph(nx_graph),
            avg_confidence=avg_confidence,
            complexity_score=complexity_score,
        )

        return WorkflowGraphMetrics(
            node_count=n_nodes,
            edge_count=n_edges,
            graph_density=density,
            average_confidence=avg_confidence,
            complexity_score=complexity_score,
            branching_factor=branching_factor,
            longest_path_length=longest_path_length,
            automation_readiness_score=automation_readiness,
        )

    @staticmethod
    def _automation_readiness(
        workflow_graph: WorkflowGraph,
        is_dag: bool,
        avg_confidence: float,
        complexity_score: float,
    ) -> float:
        if not is_dag:
            return 0.0

        # Confidence component (0..1) weighted 0.4
        conf_component = avg_confidence * 0.4

        # Simplicity: lower complexity = easier to automate; weighted 0.3
        simplicity = (1.0 - min(1.0, complexity_score)) * 0.3

        # Frequency component: more repetition = higher automation ROI; weighted 0.3
        frequency = workflow_graph.metadata.get("frequency", 0)
        freq_component = min(1.0, frequency / 100.0) * 0.3

        return round((conf_component + simplicity + freq_component) * 10.0, 2)
