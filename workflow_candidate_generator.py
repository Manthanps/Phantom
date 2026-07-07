"""WorkflowCandidateGenerator — assembles all scored components into WorkflowCandidates."""

from __future__ import annotations

from datetime import datetime

from ghostflow.pattern_discovery.generators.workflow_classifier import WorkflowClassifier
from ghostflow.pattern_discovery.graphs.graph_metrics import GraphMetrics
from ghostflow.pattern_discovery.graphs.workflow_graph_builder import WorkflowGraphBuilder
from ghostflow.pattern_discovery.models.discovered_pattern import DiscoveredPattern
from ghostflow.pattern_discovery.models.pattern_statistics import PatternStatistics
from ghostflow.pattern_discovery.models.workflow_candidate import WorkflowCandidate
from ghostflow.pattern_discovery.scoring.automation_value_estimator import AutomationValueEstimator
from ghostflow.pattern_discovery.scoring.confidence_engine import ConfidenceEngine
from ghostflow.pattern_discovery.temporal.temporal_analyzer import TemporalAnalyzer


class WorkflowCandidateGenerator:
    """Converts a DiscoveredPattern into a fully scored WorkflowCandidate.

    Pipeline per pattern::

        DiscoveredPattern
            → TemporalAnalyzer  (temporal_consistency, recurrence_type)
            → GraphBuilder      (workflow_graph)
            → GraphMetrics      (graph_consistency)
            → ConfidenceEngine  (confidence, breakdown)
            → AutomationValue   (time_saved, value_score)
            → WorkflowClassifier (category)
            → WorkflowCandidate
    """

    def __init__(
        self,
        observation_days: float = 30.0,
        seconds_per_step: float = 5.0,
    ) -> None:
        self._temporal = TemporalAnalyzer()
        self._graph_builder = WorkflowGraphBuilder()
        self._graph_metrics = GraphMetrics()
        self._confidence = ConfidenceEngine()
        self._automation = AutomationValueEstimator(
            seconds_per_step=seconds_per_step,
            observation_days=observation_days,
        )
        self._classifier = WorkflowClassifier()

    def generate(
        self,
        pattern: DiscoveredPattern,
        all_sequences: list[list[str]],
        session_timestamps: list[datetime | None] | None = None,
        contiguous_support: float | None = None,
    ) -> WorkflowCandidate:
        timestamps = session_timestamps or [None] * len(all_sequences)

        # ── Temporal analysis ─────────────────────────────────────────────────
        temporal = self._temporal.analyze(pattern, timestamps)

        # ── Graph ─────────────────────────────────────────────────────────────
        nx_graph = self._graph_builder.build(pattern, all_sequences)
        graph_dict = WorkflowGraphBuilder.to_dict(nx_graph)
        gmetrics = self._graph_metrics.compute(nx_graph)
        graph_consistency = gmetrics.get("graph_consistency", 0.0)

        # ── Confidence ────────────────────────────────────────────────────────
        breakdown = self._confidence.score(
            pattern=pattern,
            all_sequences=all_sequences,
            temporal_consistency=temporal["temporal_consistency"],
            graph_consistency=graph_consistency,
            contiguous_support=contiguous_support,
        )

        # ── Automation value ──────────────────────────────────────────────────
        av = self._automation.estimate(pattern)

        # ── Classification ────────────────────────────────────────────────────
        classification = self._classifier.classify(pattern.sequence)

        # ── Statistics ───────────────────────────────────────────────────────
        from collections import Counter

        event_dist = dict(Counter(pattern.sequence))
        stats = PatternStatistics(
            total_occurrences=pattern.frequency,
            unique_sessions=len(pattern.session_indices),
            support_ratio=pattern.support,
            first_occurrence=temporal.get("first_occurrence"),
            last_occurrence=temporal.get("last_occurrence"),
            average_interval_hours=temporal.get("average_interval_hours"),
            interval_std_hours=temporal.get("interval_std_hours"),
            recurrence_type=temporal.get("recurrence_type", "unknown"),
            event_type_distribution=event_dist,
            avg_session_length=self._avg_session_len(pattern, all_sequences),
        )

        name = self._make_name(pattern.sequence, classification)

        return WorkflowCandidate(
            sequence=pattern.sequence,
            confidence=breakdown.total,
            frequency=pattern.frequency,
            support=pattern.support,
            classification=classification,
            statistics=stats,
            confidence_breakdown=breakdown,
            name=name,
            graph_data=graph_dict,
            automation_value_score=av["automation_value_score"],
            estimated_time_saved_per_week_hours=av["estimated_time_saved_per_week_hours"],
            manual_steps_eliminated=av["manual_steps_eliminated"],
            first_seen_at=temporal.get("first_occurrence"),
            last_seen_at=temporal.get("last_occurrence"),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _avg_session_len(pattern: DiscoveredPattern, all_sequences: list[list[str]]) -> float:
        lengths = [len(all_sequences[i]) for i in pattern.session_indices if i < len(all_sequences)]
        return sum(lengths) / len(lengths) if lengths else 0.0

    @staticmethod
    def _make_name(sequence: list[str], classification: str) -> str:
        """Derive a short human-readable name from the pattern sequence."""
        steps = " → ".join(e.replace("_", " ").title() for e in sequence[:3])
        suffix = "…" if len(sequence) > 3 else ""
        return f"{steps}{suffix}"
