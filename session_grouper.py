"""SessionGrouper — clusters behaviorally similar sessions before mining."""

from __future__ import annotations

import uuid

from ghostflow.workflow_discovery.clustering.sequence_similarity import overlap_coefficient
from ghostflow.workflow_discovery.models.session_cluster import SessionCluster


class SessionGrouper:
    """
    Groups event-sequence sessions into behaviorally similar clusters using
    single-linkage agglomerative clustering on the bigram overlap coefficient.

    Algorithm:
    1. For each unassigned session, start a new cluster.
    2. Add a session to the first existing cluster that has any member
       with overlap >= similarity_threshold.  (Single-linkage: one match is enough.)
    3. Sessions that don't match any cluster become singleton clusters.

    Then compute the centroid (sequence with highest average similarity to
    others in the cluster) and internal_similarity (mean pairwise overlap).

    Default similarity_threshold = 0.35 — two sessions sharing 35% of their
    event bigrams are considered related.  Tune lower for tighter clusters.
    """

    def __init__(self, similarity_threshold: float = 0.35) -> None:
        self._threshold = similarity_threshold

    def group(
        self,
        sequences: list[list[str]],
        session_ids: list[str] | None = None,
    ) -> list[SessionCluster]:
        """Group *sequences* into clusters and return them."""
        if not sequences:
            return []

        ids = session_ids or [str(i) for i in range(len(sequences))]
        raw_clusters: list[list[int]] = []  # indices into sequences

        for idx in range(len(sequences)):
            placed = False
            for cluster in raw_clusters:
                if self._is_similar_to_any(idx, cluster, sequences):
                    cluster.append(idx)
                    placed = True
                    break
            if not placed:
                raw_clusters.append([idx])

        return [self._build_cluster(indices, sequences, ids) for indices in raw_clusters]

    # ── Internal ───────────────────────────────────────────────────────────────

    def _is_similar_to_any(self, idx: int, cluster: list[int], sequences: list[list[str]]) -> bool:
        seq = sequences[idx]
        return any(
            overlap_coefficient(seq, sequences[member]) >= self._threshold for member in cluster
        )

    def _build_cluster(
        self,
        indices: list[int],
        sequences: list[list[str]],
        session_ids: list[str],
    ) -> SessionCluster:
        seqs = [sequences[i] for i in indices]
        sids = [session_ids[i] for i in indices]

        centroid = self._find_centroid(seqs)
        internal_sim = self._mean_pairwise_similarity(seqs)

        return SessionCluster(
            cluster_id=str(uuid.uuid4()),
            sequences=seqs,
            session_ids=sids,
            centroid_sequence=centroid,
            internal_similarity=internal_sim,
            size=len(seqs),
        )

    @staticmethod
    def _find_centroid(seqs: list[list[str]]) -> list[str]:
        """Return the sequence with the highest mean similarity to all others."""
        if len(seqs) == 1:
            return seqs[0]
        best_seq, best_score = seqs[0], -1.0
        for i, seq in enumerate(seqs):
            others = [seqs[j] for j in range(len(seqs)) if j != i]
            avg_sim = sum(overlap_coefficient(seq, o) for o in others) / len(others)
            if avg_sim > best_score:
                best_score = avg_sim
                best_seq = seq
        return best_seq

    @staticmethod
    def _mean_pairwise_similarity(seqs: list[list[str]]) -> float:
        if len(seqs) <= 1:
            return 1.0
        scores: list[float] = []
        for i in range(len(seqs)):
            for j in range(i + 1, len(seqs)):
                scores.append(overlap_coefficient(seqs[i], seqs[j]))
        return round(sum(scores) / len(scores), 4) if scores else 0.0
