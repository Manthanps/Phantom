"""AutomationScorer — composite 0-10 automation score for WorkflowCandidateV2."""

from __future__ import annotations

import math

from ghostflow.workflow_discovery.models.workflow_candidate_v2 import WorkflowCandidateV2


class AutomationScorer:
    """
    Produces a single 0-10 automation score that balances four dimensions:

    | Component    | Weight | Signal                                  |
    |---|---|---|
    | Confidence   |  30%   | Discovered pattern confidence (0-1)     |
    | Frequency    |  25%   | Log-compressed weekly frequency         |
    | Consistency  |  20%   | How uniformly the sequence appears      |
    | Value        |  25%   | Estimated hours saved per week (capped) |

    Score ≥ 7.0  → high-value automation candidate
    Score 4.0-7.0 → worth investigating
    Score < 4.0  → low priority
    """

    _W_CONFIDENCE = 0.30
    _W_FREQUENCY = 0.25
    _W_CONSISTENCY = 0.20
    _W_VALUE = 0.25

    # Frequency: log1p(weekly_freq * scale) / log1p(scale)
    # At scale=20: freq=1/week→0.20, 3/week→0.48, 10/week→0.75, 50/week→1.0+
    _FREQ_SCALE = 20.0

    # Value: hours_saved * gain; capped at 1.0
    # At gain=0.25: 4h/week→1.0
    _VALUE_GAIN = 0.25

    def score(self, candidate: WorkflowCandidateV2) -> float:
        confidence_pts = candidate.confidence * 10.0 * self._W_CONFIDENCE

        freq_norm = min(
            1.0,
            math.log1p(candidate.frequency_per_week * self._FREQ_SCALE)
            / math.log1p(self._FREQ_SCALE),
        )
        freq_pts = freq_norm * 10.0 * self._W_FREQUENCY

        consistency_pts = candidate.consistency_score * 10.0 * self._W_CONSISTENCY

        value_norm = min(1.0, candidate.estimated_time_saved_per_week_hours * self._VALUE_GAIN)
        value_pts = value_norm * 10.0 * self._W_VALUE

        raw = confidence_pts + freq_pts + consistency_pts + value_pts
        return round(min(10.0, raw), 1)

    def score_all(self, candidates: list[WorkflowCandidateV2]) -> list[WorkflowCandidateV2]:
        for c in candidates:
            c.automation_score = self.score(c)
        return candidates
