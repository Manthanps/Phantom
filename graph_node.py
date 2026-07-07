"""GraphNode — a single step in a workflow graph."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    TERMINAL = "terminal"


def _infer_action_type(event_type: str) -> str:
    if event_type.startswith("file_"):
        return "file_operation"
    if event_type.startswith("folder_"):
        return "folder_operation"
    return "general_operation"


@dataclass
class GraphNode:
    node_id: str
    event_type: str
    label: str
    node_type: NodeType
    action_type: str
    path_pattern: str
    metadata: dict[str, Any]
    frequency: int
    confidence: float
    position: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "event_type": self.event_type,
            "label": self.label,
            "node_type": self.node_type.value,
            "action_type": self.action_type,
            "path_pattern": self.path_pattern,
            "metadata": self.metadata,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphNode:
        return cls(
            node_id=data["node_id"],
            event_type=data["event_type"],
            label=data.get("label", data["event_type"]),
            node_type=NodeType(data.get("node_type", NodeType.ACTION.value)),
            action_type=data.get("action_type", _infer_action_type(data["event_type"])),
            path_pattern=data.get("path_pattern", ""),
            metadata=data.get("metadata", {}),
            frequency=data.get("frequency", 0),
            confidence=data.get("confidence", 0.0),
            position=data.get("position", 0),
        )
