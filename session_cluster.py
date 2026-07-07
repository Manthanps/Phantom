"""SessionCluster — a group of behaviorally similar sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SessionCluster:
    """
    A group of sessions whose event-type sequences are behaviorally similar.

    The clustering is computed by SessionGrouper using bigram overlap coefficient.
    Mining within a tight cluster produces higher-confidence, more targeted candidates
    than mining across all sessions indiscriminately.
    """

    cluster_id: str
    sequences: list[list[str]]
    """Event-type sequences for each session in this cluster."""

    session_ids: list[str]
    """Original session IDs in the same order as sequences."""

    centroid_sequence: list[str]
    """The most representative sequence (highest average similarity to others)."""

    internal_similarity: float
    """Average pairwise overlap coefficient within the cluster (0-1)."""

    size: int
    label: str = ""
    """Auto-generated human-readable label, e.g. 'Cluster-1 (5 sessions)'."""

    def __post_init__(self) -> None:
        if not self.label:
            self.label = f"Cluster-{self.cluster_id[:6]} ({self.size} sessions)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "size": self.size,
            "label": self.label,
            "centroid_sequence": self.centroid_sequence,
            "internal_similarity": round(self.internal_similarity, 4),
            "session_ids": self.session_ids[:20],
        }
