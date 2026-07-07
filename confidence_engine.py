"""ConfidenceEngine — multi-factor confidence scoring for discovered patterns.

Formula
-------
confidence = 0.35 × repetition_score
           + 0.20 × temporal_consistency
           + 0.15 × session_similarity
           + 0.15 × sequence_stability
           + 0.15 × graph_consistency

Each component is independently bounded to [0, 1].
"""

from __future__ import annotations

import random

from ghostflow.pattern_discovery.models.confidence_breakdown import ConfidenceBreakdown
from ghostflow.pattern_discovery.models.discovered_pattern import DiscoveredPattern

# ── Edit distance (Levenshtein) ────────────────────────────────────────────────


def _edit_distance(a: list[str], b: list[str]) -> int:
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def _seq_similarity(a: list[str], b: list[str]) -> float:
    if not a and not b:
        return 1.0
    d = _edit_distance(a, b)
    return 1.0 - d / max(len(a), len(b))


class ConfidenceEngine:
    """Computes explainable, multi-factor confidence scores.

    Parameters
    ----------
    max_pairwise_sessions:
        Cap on the number of sessions used for pairwise similarity
        (prevents O(n²) slowdown on large datasets).
    """

    def __init__(self, max_pairwise_sessions: int = 30) -> None:
        self._max_pairs = max_pairwise_sessions

    def score(
        self,
        pattern: DiscoveredPattern,
        all_sequences: list[list[str]],
        temporal_consistency: float = 0.0,
        graph_consistency: float = 0.0,
        contiguous_support: float | None = None,
    ) -> ConfidenceBreakdown:
        bd = ConfidenceBreakdown()

        # 1. Repetition score
        bd.repetition_score = self._repetition(pattern.support)

        # 2. Temporal consistency (provided by TemporalAnalyzer)
        bd.temporal_consistency = max(0.0, min(1.0, temporal_consistency))

        # 3. Session similarity
        bd.session_similarity = self._session_similarity(pattern, all_sequences)

        # 4. Sequence stability
        bd.sequence_stability = self._sequence_stability(pattern, contiguous_support)

        # 5. Graph consistency (provided by GraphMetrics)
        bd.graph_consistency = max(0.0, min(1.0, graph_consistency))

        return bd.compute()

    # ── Component calculations ─────────────────────────────────────────────────

    @staticmethod
    def _repetition(support: float) -> float:
        """Non-linear repetition score — rewards consistently high support."""
        # Sigmoid-like curve: support=0.3 → 0.36, support=0.8 → 0.89, support=1.0 → 1.0
        return round(1.0 - (1.0 - support) ** 1.5, 4)

    def _session_similarity(
        self,
        pattern: DiscoveredPattern,
        all_sequences: list[list[str]],
    ) -> float:
        """Average pairwise normalised edit similarity among sessions containing pattern."""
        sids = pattern.session_indices
        seqs = [all_sequences[i] for i in sids if i < len(all_sequences)]
        if len(seqs) < 2:
            return 0.5  # neutral — not enough data

        # Sample to bound computation
        sample = seqs if len(seqs) <= self._max_pairs else random.sample(seqs, self._max_pairs)
        total, count = 0.0, 0
        for i in range(len(sample)):
            for j in range(i + 1, len(sample)):
                total += _seq_similarity(sample[i], sample[j])
                count += 1

        return round(total / count, 4) if count > 0 else 0.5

    @staticmethod
    def _sequence_stability(
        pattern: DiscoveredPattern,
        contiguous_support: float | None,
    ) -> float:
        """How often does the pattern appear contiguously vs. as a loose subsequence?"""
        if pattern.is_contiguous:
            return 1.0
        if contiguous_support is None or contiguous_support == 0:
            # Purely non-contiguous — moderate stability
            return 0.4
        return round(min(1.0, contiguous_support / max(pattern.support, 1e-9)), 4)
