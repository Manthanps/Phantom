"""EvolutionDetector — classifies how a workflow has changed since last observed."""

from __future__ import annotations

from typing import Any

from ghostflow.workflow_discovery.clustering.sequence_similarity import jaccard
from ghostflow.workflow_discovery.models.workflow_candidate_v2 import (
    EvolutionStatus,
    WorkflowCandidateV2,
)
from ghostflow.workflow_discovery.models.workflow_evolution import WorkflowEvolution


class EvolutionDetector:
    """
    Compares newly discovered workflow candidates against previously known ones
    (provided as a list of dicts from WorkflowCandidate.to_dict()).

    Decision logic per candidate:
    - No match (similarity < match_threshold)    → NEW
    - Multiple new candidates matched same old   → BRANCHING for both
    - Frequency up > 20%                         → GROWING
    - Frequency down > 20%                       → DECLINING
    - Otherwise                                  → STABLE

    The frequency comparison is done in absolute counts.  If historical
    candidates have no frequency, all matches default to STABLE.
    """

    _MATCH_THRESHOLD = 0.50  # minimum overlap to consider a historical match
    _GROWTH_THRESHOLD = 0.20  # 20% frequency increase → GROWING
    _DECLINE_THRESHOLD = -0.20  # 20% decrease → DECLINING

    def detect(
        self,
        new_candidates: list[WorkflowCandidateV2],
        historical: list[dict[str, Any]],
    ) -> list[WorkflowEvolution]:
        """
        Returns a WorkflowEvolution for every candidate in *new_candidates*.
        Candidates that match no historical record get status=NEW.
        """
        if not historical:
            return [self._make_new(c) for c in new_candidates]

        # Build historical lookup: sequence tuple → dict
        hist_by_seq: dict[tuple[str, ...], dict[str, Any]] = {
            tuple(h.get("sequence", [])): h for h in historical
        }

        # Track which historical entries are matched by multiple new candidates
        # → BRANCHING signal
        hist_match_count: dict[tuple[str, ...], int] = {}
        matched_new_to_hist: dict[str, tuple[str, ...]] = {}  # candidate_id → hist_seq

        for nc in new_candidates:
            best_seq, best_sim = self._find_best_match(nc.sequence, hist_by_seq)
            if best_seq is not None and best_sim >= self._MATCH_THRESHOLD:
                matched_new_to_hist[nc.candidate_id] = best_seq
                hist_match_count[best_seq] = hist_match_count.get(best_seq, 0) + 1

        # Build evolution records
        evolutions: list[WorkflowEvolution] = []
        for nc in new_candidates:
            hist_seq = matched_new_to_hist.get(nc.candidate_id)
            if hist_seq is None:
                evolutions.append(self._make_new(nc))
                continue

            hist = hist_by_seq[hist_seq]
            is_branching = hist_match_count.get(hist_seq, 0) > 1
            evolutions.append(self._compare(nc, hist, branching=is_branching))

        return evolutions

    # ── Internal ───────────────────────────────────────────────────────────────

    def _find_best_match(
        self,
        sequence: list[str],
        hist_by_seq: dict[tuple[str, ...], dict[str, Any]],
    ) -> tuple[tuple[str, ...] | None, float]:
        """Use Jaccard unigram similarity for matching — captures 'same event types'
        even when steps are added/removed, which is exactly the evolution case."""
        best_seq: tuple[str, ...] | None = None
        best_sim = 0.0
        for hist_seq in hist_by_seq:
            sim = jaccard(sequence, list(hist_seq))
            if sim > best_sim:
                best_sim = sim
                best_seq = hist_seq
        return best_seq, best_sim

    def _compare(
        self,
        nc: WorkflowCandidateV2,
        hist: dict[str, Any],
        branching: bool,
    ) -> WorkflowEvolution:
        prev_freq = int(hist.get("frequency", 0))
        curr_freq = nc.frequency
        prev_conf = float(hist.get("confidence", 0.0))
        curr_conf = nc.confidence
        hist_seq: list[str] = hist.get("sequence", [])

        freq_trend = (curr_freq - prev_freq) / max(1, prev_freq) if prev_freq > 0 else 0.0
        conf_trend = curr_conf - prev_conf

        steps_added = [s for s in nc.sequence if s not in hist_seq]
        steps_removed = [s for s in hist_seq if s not in nc.sequence]

        if branching:
            status = EvolutionStatus.BRANCHING
            notes = (
                f"Workflow branched — multiple new variants match the historical "
                f"'{hist.get('name', 'workflow')}' pattern."
            )
        elif freq_trend > self._GROWTH_THRESHOLD:
            status = EvolutionStatus.GROWING
            notes = (
                f"Frequency increased from {prev_freq} to {curr_freq} "
                f"(+{freq_trend:.0%}). Automation value is expanding."
            )
        elif freq_trend < self._DECLINE_THRESHOLD:
            status = EvolutionStatus.DECLINING
            notes = (
                f"Frequency dropped from {prev_freq} to {curr_freq} "
                f"({freq_trend:.0%}). May already be partially automated."
            )
        else:
            status = EvolutionStatus.STABLE
            notes = f"Pattern is stable (prev={prev_freq}, curr={curr_freq}, Δ={freq_trend:+.0%})."

        if steps_added:
            notes += f" Steps added: {steps_added}."
        if steps_removed:
            notes += f" Steps removed: {steps_removed}."

        return WorkflowEvolution(
            candidate_id=nc.candidate_id,
            status=status,
            previous_frequency=prev_freq,
            current_frequency=curr_freq,
            frequency_trend=round(freq_trend, 4),
            trend_direction=(
                "up" if freq_trend > 0.05 else "down" if freq_trend < -0.05 else "flat"
            ),
            steps_added=steps_added,
            steps_removed=steps_removed,
            previous_confidence=prev_conf,
            current_confidence=curr_conf,
            confidence_trend=round(conf_trend, 4),
            notes=notes,
        )

    @staticmethod
    def _make_new(nc: WorkflowCandidateV2) -> WorkflowEvolution:
        return WorkflowEvolution(
            candidate_id=nc.candidate_id,
            status=EvolutionStatus.NEW,
            previous_frequency=0,
            current_frequency=nc.frequency,
            frequency_trend=1.0,
            trend_direction="up",
            notes="First time this workflow pattern has been observed.",
        )
