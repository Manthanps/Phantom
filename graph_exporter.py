"""GraphExporter — text-format visualization exports (Mermaid, DOT)."""

from __future__ import annotations

from ghostflow.workflow_graph.models.graph_node import NodeType
from ghostflow.workflow_graph.models.workflow_graph import WorkflowGraph


def _mermaid_shape(node_type: NodeType) -> tuple[str, str]:
    """Return Mermaid shape delimiters for a node type."""
    if node_type in (NodeType.TRIGGER, NodeType.TERMINAL):
        return "([", "])"  # stadium shape — visually distinct start/end
    if node_type == NodeType.CONDITION:
        return "{", "}"  # rhombus — decision
    return "[", "]"  # rectangle — action


class GraphExporter:
    """Exports a WorkflowGraph to human-readable text formats.

    Supported formats:
    - Mermaid flowchart (``flowchart TD``)
    - GraphViz DOT
    """

    @staticmethod
    def to_mermaid(workflow_graph: WorkflowGraph) -> str:
        """Export as a Mermaid flowchart string.

        Example output::

            flowchart TD
                n0([File Created])
                n1[File Modified]
                n2([File Moved])
                n0 --> n1
                n1 --> n2
        """
        lines = ["flowchart TD"]

        for node in workflow_graph.nodes:
            open_s, close_s = _mermaid_shape(node.node_type)
            # Escape special Mermaid characters in the label
            label = node.label.replace('"', "'")
            lines.append(f"    {node.node_id}{open_s}{label}{close_s}")

        for edge in workflow_graph.edges:
            lines.append(f"    {edge.source_node_id} --> {edge.target_node_id}")

        return "\n".join(lines)

    @staticmethod
    def to_dot(workflow_graph: WorkflowGraph) -> str:
        """Export as a GraphViz DOT string.

        Example output::

            digraph "Research Workflow" {
                rankdir=LR;
                node [shape=box, style=filled, fillcolor=lightblue];
                "n0" [label="File Created", shape=oval, fillcolor=lightgreen];
                "n1" [label="File Modified"];
                "n2" [label="File Moved", shape=oval, fillcolor=lightcoral];
                "n0" -> "n1";
                "n1" -> "n2";
            }
        """
        safe_name = workflow_graph.name.replace('"', '\\"')
        lines = [f'digraph "{safe_name}" {{']
        lines.append("    rankdir=LR;")
        lines.append("    node [shape=box, style=filled, fillcolor=lightblue];")

        for node in workflow_graph.nodes:
            label = node.label.replace('"', '\\"')
            extras = ""
            if node.node_type == NodeType.TRIGGER:
                extras = ", shape=oval, fillcolor=lightgreen"
            elif node.node_type == NodeType.TERMINAL:
                extras = ", shape=oval, fillcolor=lightcoral"
            lines.append(f'    "{node.node_id}" [label="{label}"{extras}];')

        for edge in workflow_graph.edges:
            lines.append(f'    "{edge.source_node_id}" -> "{edge.target_node_id}";')

        lines.append("}")
        return "\n".join(lines)
