"""GraphValidator — structural integrity checks for WorkflowGraph."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import networkx as nx

from ghostflow.workflow_graph.models.workflow_graph import WorkflowGraph


class ValidationSeverity(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class GraphValidationResult:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    severity: ValidationSeverity = ValidationSeverity.OK

    def _refresh_severity(self) -> None:
        if self.errors:
            self.severity = ValidationSeverity.ERROR
        elif self.warnings:
            self.severity = ValidationSeverity.WARNING
        else:
            self.severity = ValidationSeverity.OK

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "severity": self.severity.value,
        }


class GraphValidator:
    """Validates structural integrity of a WorkflowGraph.

    Checks performed:
    1. At least 2 nodes
    2. At least 1 edge
    3. No duplicate node IDs
    4. No duplicate edge IDs
    5. All edges reference valid node IDs
    6. Graph is a DAG (no cycles)
    7. No orphan (isolated) nodes (warning only)
    """

    def validate(self, workflow_graph: WorkflowGraph) -> GraphValidationResult:
        result = GraphValidationResult()

        # ── 1. Minimum nodes ─────────────────────────────────────────────────
        if len(workflow_graph.nodes) < 2:
            result.errors.append(
                f"Graph must have at least 2 nodes (found {len(workflow_graph.nodes)})."
            )
            result.is_valid = False

        # ── 2. Minimum edges ─────────────────────────────────────────────────
        if len(workflow_graph.edges) < 1:
            result.errors.append(
                f"Graph must have at least 1 edge (found {len(workflow_graph.edges)})."
            )
            result.is_valid = False

        # ── 3. Duplicate node IDs ─────────────────────────────────────────────
        node_ids = [n.node_id for n in workflow_graph.nodes]
        seen: set[str] = set()
        dupes: list[str] = []
        for nid in node_ids:
            if nid in seen:
                dupes.append(nid)
            seen.add(nid)
        if dupes:
            result.errors.append(f"Duplicate node IDs: {sorted(set(dupes))}")
            result.is_valid = False

        # ── 4. Duplicate edge IDs ─────────────────────────────────────────────
        edge_ids = [e.edge_id for e in workflow_graph.edges]
        seen_e: set[str] = set()
        dupe_e: list[str] = []
        for eid in edge_ids:
            if eid in seen_e:
                dupe_e.append(eid)
            seen_e.add(eid)
        if dupe_e:
            result.errors.append(f"Duplicate edge IDs: {sorted(set(dupe_e))}")
            result.is_valid = False

        # ── 5. Edges reference valid nodes ────────────────────────────────────
        valid_node_ids = set(node_ids)
        for edge in workflow_graph.edges:
            if edge.source_node_id not in valid_node_ids:
                result.errors.append(
                    f"Edge '{edge.edge_id}' references unknown source node '{edge.source_node_id}'."
                )
                result.is_valid = False
            if edge.target_node_id not in valid_node_ids:
                result.errors.append(
                    f"Edge '{edge.edge_id}' references unknown target node '{edge.target_node_id}'."
                )
                result.is_valid = False

        # ── 6 & 7. DAG + orphan checks (only when basic structure is valid) ───
        if result.is_valid:
            nx_graph = workflow_graph.to_networkx()

            if not nx.is_directed_acyclic_graph(nx_graph):
                result.errors.append(
                    "Graph contains cycles and is not a DAG. Execution order is undefined."
                )
                result.is_valid = False

            orphans = [n for n in nx_graph.nodes if nx_graph.in_degree(n) == 0 and nx_graph.out_degree(n) == 0]
            if orphans:
                result.warnings.append(f"Orphan (disconnected) nodes: {sorted(orphans)}")

        result._refresh_severity()
        return result
