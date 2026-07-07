"""ExecutionOrderResolver — topological execution plan from a WorkflowGraph."""

from __future__ import annotations

import networkx as nx

from ghostflow.workflow_graph.models.execution_plan import ExecutionPlan, ExecutionStep
from ghostflow.workflow_graph.models.workflow_graph import WorkflowGraph


class ExecutionOrderResolver:
    """Produces a dependency-ordered ExecutionPlan from a WorkflowGraph.

    Fails safely (``can_execute=False``) when:
    - The graph has no nodes.
    - The graph contains cycles (not a DAG).
    - Topological sort is otherwise infeasible.
    """

    def resolve(self, workflow_graph: WorkflowGraph) -> ExecutionPlan:
        plan = ExecutionPlan(graph_id=workflow_graph.graph_id)

        nx_graph = workflow_graph.to_networkx()

        if not nx_graph.nodes:
            plan.can_execute = False
            plan.errors.append("Graph has no nodes — nothing to execute.")
            return plan

        if not nx.is_directed_acyclic_graph(nx_graph):
            plan.can_execute = False
            plan.errors.append(
                "Graph is not a DAG (contains cycles). Execution order cannot be determined safely."
            )
            return plan

        try:
            order: list[str] = list(nx.topological_sort(nx_graph))
        except nx.NetworkXUnfeasible as exc:
            plan.can_execute = False
            plan.errors.append(f"Topological sort failed: {exc}")
            return plan

        plan.ordered_node_ids = order

        for step_num, node_id in enumerate(order, start=1):
            node = workflow_graph.get_node(node_id)
            if node is None:
                plan.warnings.append(
                    f"Node '{node_id}' appears in topological order but not in graph nodes."
                )
                continue
            plan.steps.append(
                ExecutionStep(
                    step_number=step_num,
                    node_id=node_id,
                    event_type=node.event_type,
                    label=node.label,
                    dependencies=list(nx_graph.predecessors(node_id)),
                )
            )

        plan.can_execute = True
        return plan
