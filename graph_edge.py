"""GraphEdge — a directed transition between two workflow nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TransitionType(str, Enum):
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    OPTIONAL = "optional"


@dataclass
class GraphEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    transition_type: TransitionType
    frequency: int
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "transition_type": self.transition_type.value,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphEdge:
        return cls(
            edge_id=data["edge_id"],
            source_node_id=data["source_node_id"],
            target_node_id=data["target_node_id"],
            transition_type=TransitionType(
                data.get("transition_type", TransitionType.SEQUENTIAL.value)
            ),
            frequency=data.get("frequency", 0),
            confidence=data.get("confidence", 0.0),
            metadata=data.get("metadata", {}),
        )
