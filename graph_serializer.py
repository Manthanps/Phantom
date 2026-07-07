"""GraphSerializer — converts WorkflowGraph to/from dict, JSON, and NetworkX node-link."""

from __future__ import annotations

import json
from typing import Any

from networkx.readwrite import json_graph

from ghostflow.workflow_graph.models.graph_edge import GraphEdge
from ghostflow.workflow_graph.models.graph_node import GraphNode
from ghostflow.workflow_graph.models.workflow_graph import WorkflowGraph


class GraphSerializer:
    """Serialization round-trips for WorkflowGraph.

    Preserved fields:
        graph_id, candidate_id, name, nodes, edges, execution_order,
        is_dag, complexity_score, confidence, metadata, created_at
    """

    @staticmethod
    def to_dict(workflow_graph: WorkflowGraph) -> dict[str, Any]:
        return workflow_graph.to_dict()

    @staticmethod
    def to_json(workflow_graph: WorkflowGraph, indent: int = 2) -> str:
        return json.dumps(workflow_graph.to_dict(), indent=indent)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> WorkflowGraph:
        nodes = [GraphNode.from_dict(n) for n in data.get("nodes", [])]
        edges = [GraphEdge.from_dict(e) for e in data.get("edges", [])]
        return WorkflowGraph(
            graph_id=data["graph_id"],
            candidate_id=data.get("candidate_id", ""),
            name=data.get("name", ""),
            nodes=nodes,
            edges=edges,
            execution_order=data.get("execution_order", []),
            is_dag=data.get("is_dag", True),
            complexity_score=data.get("complexity_score", 0.0),
            confidence=data.get("confidence", 0.0),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
        )

    @staticmethod
    def from_json(json_string: str) -> WorkflowGraph:
        return GraphSerializer.from_dict(json.loads(json_string))

    @staticmethod
    def to_networkx_format(workflow_graph: WorkflowGraph) -> dict[str, Any]:
        """Serialize as NetworkX node-link JSON (interoperable with D3.js etc.)."""
        nx_graph = workflow_graph.to_networkx()
        return json_graph.node_link_data(nx_graph, edges="links")
