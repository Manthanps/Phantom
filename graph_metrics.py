"""WorkflowGraphMetrics — rich structural and readiness metrics for a WorkflowGraph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WorkflowGraphMetrics:
    node_count: int = 0
    edge_count: int = 0
    graph_density: float = 0.0
    average_confidence: float = 0.0
    complexity_score: float = 0.0
    branching_factor: float = 0.0
    longest_path_length: int = 0
    automation_readiness_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "graph_density": self.graph_density,
            "average_confidence": self.average_confidence,
            "complexity_score": self.complexity_score,
            "branching_factor": self.branching_factor,
            "longest_path_length": self.longest_path_length,
            "automation_readiness_score": self.automation_readiness_score,
        }
