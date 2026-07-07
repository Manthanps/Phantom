"""ExecutionPlan — ordered, dependency-aware steps for workflow execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionStep:
    step_number: int
    node_id: str
    event_type: str
    label: str
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "node_id": self.node_id,
            "event_type": self.event_type,
            "label": self.label,
            "dependencies": self.dependencies,
        }


@dataclass
class ExecutionPlan:
    graph_id: str
    ordered_node_ids: list[str] = field(default_factory=list)
    steps: list[ExecutionStep] = field(default_factory=list)
    can_execute: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "ordered_node_ids": self.ordered_node_ids,
            "steps": [s.to_dict() for s in self.steps],
            "can_execute": self.can_execute,
            "warnings": self.warnings,
            "errors": self.errors,
        }
