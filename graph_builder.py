"""GraphBuilder — converts a WorkflowCandidate into a WorkflowGraph domain model."""

from __future__ import annotations

import uuid
from typing import Any

from ghostflow.workflow_graph.models.graph_edge import GraphEdge, TransitionType
from ghostflow.workflow_graph.models.graph_node import GraphNode, NodeType, _infer_action_type
from ghostflow.workflow_graph.models.workflow_graph import WorkflowGraph


def _make_label(event_type: str) -> str:
    return event_type.replace("_", " ").title() if event_type else "Unknown"


class GraphBuilder:
    """Builds a WorkflowGraph from any object with a compatible WorkflowCandidate interface.

    The builder reads these attributes from the candidate:
        sequence        list[str]       required
        candidate_id    str             required
        confidence      float           required
        frequency       int             required
        support         float           required
        name            str             optional (default: derived from sequence[0])
        classification  str             optional
        automation_value_score  float   optional
    """

    def build(self, candidate: Any) -> WorkflowGraph:
        sequence: list[str] = getattr(candidate, "sequence", [])
        candidate_id: str = getattr(candidate, "candidate_id", str(uuid.uuid4()))
        confidence: float = float(getattr(candidate, "confidence", 0.0))
        frequency: int = int(getattr(candidate, "frequency", 0))
        support: float = float(getattr(candidate, "support", 0.0))
        name: str = getattr(candidate, "name", "") or (
            _make_label(sequence[0]) if sequence else "Empty Workflow"
        )

        graph = WorkflowGraph(
            graph_id=str(uuid.uuid4()),
            candidate_id=candidate_id,
            name=name,
            confidence=confidence,
            metadata={
                "classification": getattr(candidate, "classification", ""),
                "support": support,
                "automation_value_score": float(getattr(candidate, "automation_value_score", 0.0)),
                "frequency": frequency,
            },
        )

        if not sequence:
            graph.is_dag = True
            return graph

        n = len(sequence)
        node_ids: list[str] = []

        # ── Nodes ─────────────────────────────────────────────────────────────
        for i, event_type in enumerate(sequence):
            node_id = f"n{i}"
            if i == 0:
                node_type = NodeType.TRIGGER
            elif i == n - 1:
                node_type = NodeType.TERMINAL
            else:
                node_type = NodeType.ACTION

            graph.add_node(
                GraphNode(
                    node_id=node_id,
                    event_type=event_type,
                    label=_make_label(event_type),
                    node_type=node_type,
                    action_type=_infer_action_type(event_type),
                    path_pattern="",
                    metadata={},
                    frequency=frequency,
                    confidence=confidence,
                    position=i,
                )
            )
            node_ids.append(node_id)

        # ── Edges ─────────────────────────────────────────────────────────────
        for i in range(n - 1):
            src_id = node_ids[i]
            dst_id = node_ids[i + 1]
            graph.add_edge(
                GraphEdge(
                    edge_id=f"{src_id}__{dst_id}",
                    source_node_id=src_id,
                    target_node_id=dst_id,
                    transition_type=TransitionType.SEQUENTIAL,
                    frequency=frequency,
                    confidence=confidence,
                )
            )

        # Linear chains are always DAGs
        graph.is_dag = True
        graph.execution_order = list(node_ids)

        # Complexity = edge count / max possible directed edges (graph density)
        if n > 1:
            max_edges = n * (n - 1)
            graph.complexity_score = round((n - 1) / max_edges, 4)

        return graph
