"""WorkflowEvolution — how a workflow candidate changed since it was last observed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ghostflow.workflow_discovery.models.workflow_candidate_v2 import EvolutionStatus


@dataclass
class WorkflowEvolution:
    """
    Evolution record comparing a new candidate against its historical version.

    Produced by EvolutionDetector for every candidate that matches a previously
    persisted workflow.  Candidates with no historical match get status=NEW.
    """

    candidate_id: str
    status: EvolutionStatus

    # Frequency comparison
    previous_frequency: int
    current_frequency: int
    frequency_trend: float
    """(current - previous) / previous; positive = growing, negative = declining."""

    trend_direction: str
    """'up' | 'down' | 'flat'."""

    # Sequence comparison
    steps_added: list[str] = field(default_factory=list)
    steps_removed: list[str] = field(default_factory=list)

    # Confidence comparison
    previous_confidence: float = 0.0
    current_confidence: float = 0.0
    confidence_trend: float = 0.0

    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "status": self.status.value,
            "previous_frequency": self.previous_frequency,
            "current_frequency": self.current_frequency,
            "frequency_trend": round(self.frequency_trend, 4),
            "trend_direction": self.trend_direction,
            "steps_added": self.steps_added,
            "steps_removed": self.steps_removed,
            "previous_confidence": round(self.previous_confidence, 4),
            "current_confidence": round(self.current_confidence, 4),
            "confidence_trend": round(self.confidence_trend, 4),
            "notes": self.notes,
        }
