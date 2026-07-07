"""DiscoveryReport — full output of the Workflow Discovery Agent V2 pipeline."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ghostflow.workflow_discovery.models.workflow_candidate_v2 import WorkflowCandidateV2
from ghostflow.workflow_discovery.models.workflow_evolution import WorkflowEvolution


@dataclass
class DiscoveryReport:
    """
    Aggregated output of one discovery run.

    Contains all ranked workflow candidates, cluster summaries, evolution
    records, and aggregate value metrics (total weekly hours saved, etc.).
    """

    # Input stats
    total_events: int
    total_sessions: int

    # Clustering
    clusters_found: int
    cluster_summaries: list[dict[str, Any]]

    # Candidates — sorted by automation_score descending
    candidates: list[WorkflowCandidateV2]

    # Evolution
    evolution_summaries: list[WorkflowEvolution]

    # Performance
    elapsed_seconds: float
    discovery_config: dict[str, Any] = field(default_factory=dict)

    # Auto-computed
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def top_candidate(self) -> WorkflowCandidateV2 | None:
        return self.candidates[0] if self.candidates else None

    @property
    def total_estimated_weekly_hours_saved(self) -> float:
        return round(sum(c.estimated_time_saved_per_week_hours for c in self.candidates), 2)

    @property
    def high_value_count(self) -> int:
        return sum(1 for c in self.candidates if c.automation_score >= 7.0)

    @property
    def new_workflows_count(self) -> int:
        from ghostflow.workflow_discovery.models.workflow_candidate_v2 import EvolutionStatus

        return sum(1 for c in self.candidates if c.evolution_status == EvolutionStatus.NEW)

    @property
    def evolving_workflows_count(self) -> int:
        from ghostflow.workflow_discovery.models.workflow_candidate_v2 import EvolutionStatus

        return sum(
            1
            for c in self.candidates
            if c.evolution_status in (EvolutionStatus.GROWING, EvolutionStatus.BRANCHING)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "total_events": self.total_events,
            "total_sessions": self.total_sessions,
            "clusters_found": self.clusters_found,
            "cluster_summaries": self.cluster_summaries,
            "candidates": [c.to_dict() for c in self.candidates],
            "top_candidate": self.top_candidate.to_dict() if self.top_candidate else None,
            "total_estimated_weekly_hours_saved": self.total_estimated_weekly_hours_saved,
            "total_workflows_discovered": len(self.candidates),
            "high_value_count": self.high_value_count,
            "new_workflows_count": self.new_workflows_count,
            "evolving_workflows_count": self.evolving_workflows_count,
            "evolution_summaries": [e.to_dict() for e in self.evolution_summaries],
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "discovery_config": self.discovery_config,
        }
