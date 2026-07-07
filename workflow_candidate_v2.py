"""WorkflowCandidateV2 — enriched workflow candidate produced by Discovery Agent V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvolutionStatus(str, Enum):
    NEW = "new"
    """First time this workflow pattern has been observed."""

    STABLE = "stable"
    """Frequency and shape have remained consistent over time."""

    GROWING = "growing"
    """Occurrence frequency is increasing — automation opportunity is expanding."""

    DECLINING = "declining"
    """Occurrence frequency is decreasing — may be going away or already automated."""

    BRANCHING = "branching"
    """The workflow is splitting into multiple variants."""


@dataclass
class WorkflowCandidateV2:
    """
    A workflow candidate produced by the V2 Discovery Agent.

    Extends V1 WorkflowCandidate with:
    - cluster_id and supporting_sessions (which sessions produced it)
    - automation_score  (0-10 composite: confidence + frequency + consistency + value)
    - frequency_per_week (annualised from first/last seen)
    - consistency_score  (how uniformly the sequence repeats)
    - temporal_pattern   (daily / weekly / frequent / irregular)
    - evolution_status + evolution_notes
    - intent            (plain-English purpose, e.g. "Research Paper Processing")
    """

    candidate_id: str
    name: str
    sequence: list[str]

    # Frequency
    frequency: int
    frequency_per_week: float
    sessions_count: int
    supporting_sessions: list[str] = field(default_factory=list)

    # Confidence
    confidence: float = 0.0
    consistency_score: float = 0.0
    temporal_pattern: str = "unknown"

    # Scoring
    automation_score: float = 0.0
    """0-10 composite score: the primary ranking signal."""

    estimated_time_saved_per_week_hours: float = 0.0
    manual_steps_eliminated: int = 0
    automation_value_score: float = 0.0

    # Classification
    classification: str = "unknown"
    intent: str = ""

    # Evolution
    evolution_status: EvolutionStatus = EvolutionStatus.NEW
    evolution_notes: str = ""

    # Cluster
    cluster_id: str = ""

    # Timestamps
    first_seen_at: str | None = None
    last_seen_at: str | None = None

    # V1 compatibility passthrough
    confidence_breakdown: dict[str, Any] = field(default_factory=dict)
    statistics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "name": self.name,
            "sequence": self.sequence,
            "frequency": self.frequency,
            "frequency_per_week": round(self.frequency_per_week, 2),
            "sessions_count": self.sessions_count,
            "confidence": round(self.confidence, 4),
            "consistency_score": round(self.consistency_score, 4),
            "temporal_pattern": self.temporal_pattern,
            "automation_score": round(self.automation_score, 1),
            "estimated_time_saved_per_week_hours": round(
                self.estimated_time_saved_per_week_hours, 3
            ),
            "manual_steps_eliminated": self.manual_steps_eliminated,
            "automation_value_score": round(self.automation_value_score, 2),
            "classification": self.classification,
            "intent": self.intent,
            "evolution_status": self.evolution_status.value,
            "evolution_notes": self.evolution_notes,
            "cluster_id": self.cluster_id,
            "supporting_sessions": self.supporting_sessions[:10],
            "first_seen_at": self.first_seen_at,
            "last_seen_at": self.last_seen_at,
            "confidence_breakdown": self.confidence_breakdown,
            "statistics": self.statistics,
        }
