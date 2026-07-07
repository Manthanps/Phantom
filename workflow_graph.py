"""WorkflowGraph — rich domain model for an executable workflow graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import networkx as nx

from ghostflow.workflow_graph.models.graph_edge import GraphEdge
from ghostflow.workflow_graph.models.graph_node import GraphNode


@dataclass
class WorkflowGraph:
    graph_id: str
    candidate_id: str
    name: str
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    execution_order: list[str] = field(default_factory=list)
    is_dag: bool = True
    complexity_score: float = 0.0
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def add_node(self, node: GraphNode) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> GraphNode | None:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    def get_edges(self, source_node_id: str | None = None) -> list[GraphEdge]:
        """Return all edges, or only those originating from *source_node_id*."""
        if source_node_id is None:
            return list(self.edges)
        return [e for e in self.edges if e.source_node_id == source_node_id]

    # ── NetworkX conversion ───────────────────────────────────────────────────

    def to_networkx(self) -> nx.DiGraph:
        nx_graph: nx.DiGraph = nx.DiGraph()
        for node in self.nodes:
            nx_graph.add_node(
                node.node_id,
                event_type=node.event_type,
                label=node.label,
                node_type=node.node_type.value,
                action_type=node.action_type,
                frequency=node.frequency,
                confidence=node.confidence,
                position=node.position,
            )
        for edge in self.edges:
            nx_graph.add_edge(
                edge.source_node_id,
                edge.target_node_id,
                edge_id=edge.edge_id,
                transition_type=edge.transition_type.value,
                frequency=edge.frequency,
                confidence=edge.confidence,
            )
        return nx_graph

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "candidate_id": self.candidate_id,
            "name": self.name,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "execution_order": self.execution_order,
            "is_dag": self.is_dag,
            "complexity_score": self.complexity_score,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }
