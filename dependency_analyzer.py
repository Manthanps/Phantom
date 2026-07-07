"""DependencyAnalyzer — maps parent-child relationships and detects graph anomalies."""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from ghostflow.workflow_graph.models.workflow_graph import WorkflowGraph


@dataclass
class DependencyAnalysisResult:
    trigger_nodes: list[str] = field(default_factory=list)
    terminal_nodes: list[str] = field(default_factory=list)
    orphan_nodes: list[str] = field(default_factory=list)
    unreachable_nodes: list[str] = field(default_factory=list)
    dependency_map: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "trigger_nodes": self.trigger_nodes,
            "terminal_nodes": self.terminal_nodes,
            "orphan_nodes": self.orphan_nodes,
            "unreachable_nodes": self.unreachable_nodes,
            "dependency_map": self.dependency_map,
            "warnings": self.warnings,
        }


class DependencyAnalyzer:
    """Identifies required dependencies, entry/exit points, and disconnected nodes."""

    def analyze(self, workflow_graph: WorkflowGraph) -> DependencyAnalysisResult:
        result = DependencyAnalysisResult()
        nx_graph = workflow_graph.to_networkx()

        if not nx_graph.nodes:
            result.warnings.append("Graph has no nodes.")
            return result

        # Entry / exit classification
        result.trigger_nodes = [n for n in nx_graph.nodes if nx_graph.in_degree(n) == 0]
        result.terminal_nodes = [n for n in nx_graph.nodes if nx_graph.out_degree(n) == 0]

        # Orphans: isolated nodes (no edges at all)
        result.orphan_nodes = [n for n in nx_graph.nodes if nx_graph.in_degree(n) == 0 and nx_graph.out_degree(n) == 0]

        # Unreachable: nodes that cannot be reached from any trigger
        if result.trigger_nodes:
            reachable: set[str] = set()
            for trigger in result.trigger_nodes:
                reachable.add(trigger)
                reachable.update(nx.descendants(nx_graph, trigger))
            result.unreachable_nodes = [n for n in nx_graph.nodes if n not in reachable]
        else:
            result.unreachable_nodes = list(nx_graph.nodes)

        # Dependency map: each node → list of direct predecessor node_ids
        for node_id in nx_graph.nodes:
            result.dependency_map[node_id] = list(nx_graph.predecessors(node_id))

        # Warnings
        if result.orphan_nodes:
            result.warnings.append(f"Orphan (isolated) nodes detected: {result.orphan_nodes}")
        if result.unreachable_nodes:
            result.warnings.append(f"Unreachable nodes detected: {result.unreachable_nodes}")
        if len(result.trigger_nodes) > 1:
            result.warnings.append(f"Multiple trigger (entry) nodes: {result.trigger_nodes}")

        return result
