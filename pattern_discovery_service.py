"""PatternDiscoveryService — main orchestrator for the Pattern Discovery Layer."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from ghostflow.pattern_discovery.generators.workflow_candidate_generator import (
    WorkflowCandidateGenerator,
)
from ghostflow.pattern_discovery.mining.sequence_database import SequenceDatabase
from ghostflow.pattern_discovery.mining.workflow_miner import WorkflowMiner
from ghostflow.pattern_discovery.models.workflow_candidate import WorkflowCandidate

logger = logging.getLogger(__name__)


class PatternDiscoveryService:
    """Orchestrates the full pattern discovery pipeline.

    Usage::

        service = PatternDiscoveryService()
        candidates = service.discover_patterns(
            sequences=[["file_created", "file_modified", "file_moved"], ...],
        )

    Storage integration (optional)::

        db = SequenceDatabase.from_storage(storage_service)
        candidates = service.discover_from_database(db)
        service.persist(candidates, storage_service)
    """

    def __init__(
        self,
        min_support: float = 0.3,
        min_length: int = 2,
        max_length: int = 8,
        min_frequency: int = 3,
        observation_days: float = 30.0,
        seconds_per_step: float = 5.0,
        use_prefixspan: bool = True,
    ) -> None:
        self._miner = WorkflowMiner(
            min_support=min_support,
            min_length=min_length,
            max_length=max_length,
            min_frequency=min_frequency,
            use_prefixspan=use_prefixspan,
        )
        self._generator = WorkflowCandidateGenerator(
            observation_days=observation_days,
            seconds_per_step=seconds_per_step,
        )
        self.min_support = min_support
        self.min_frequency = min_frequency

    # ── Primary API ───────────────────────────────────────────────────────────

    def discover_patterns(
        self,
        sequences: list[list[str]],
        session_ids: list[str] | None = None,
        session_timestamps: list[datetime | None] | None = None,
        top_k: int = 20,
    ) -> list[WorkflowCandidate]:
        """Discover workflow candidates from in-memory sequences.

        Parameters
        ----------
        sequences:
            One list of event-type strings per session.
        session_ids:
            Optional session identifiers (same order as sequences).
        session_timestamps:
            Optional UTC datetimes for each session start.
        top_k:
            Maximum number of candidates to return, ranked by rank_score.
        """
        if not sequences:
            return []

        t0 = time.monotonic()
        timestamps = session_timestamps or [None] * len(sequences)

        logger.info(
            "PatternDiscovery: mining %d sessions (min_support=%.2f, min_freq=%d)",
            len(sequences),
            self.min_support,
            self.min_frequency,
        )

        patterns = self._miner.mine(sequences)
        logger.info("Found %d raw patterns; generating candidates", len(patterns))

        # Build a lookup for contiguous support (to feed sequence_stability)
        contiguous_support: dict[tuple[str, ...], float] = {
            p.key(): p.support for p in patterns if p.is_contiguous
        }

        candidates: list[WorkflowCandidate] = []
        for p in patterns:
            try:
                c_support = contiguous_support.get(p.key())
                cand = self._generator.generate(
                    pattern=p,
                    all_sequences=sequences,
                    session_timestamps=timestamps,
                    contiguous_support=c_support,
                )
                candidates.append(cand)
            except Exception as exc:
                logger.warning("Failed to generate candidate for %s: %s", p.sequence, exc)

        # Sort by combined rank_score; take top_k
        candidates.sort(key=lambda c: c.rank_score, reverse=True)
        elapsed = time.monotonic() - t0
        logger.info(
            "PatternDiscovery complete: %d candidates in %.2fs",
            len(candidates[:top_k]),
            elapsed,
        )
        return candidates[:top_k]

    def discover_from_database(
        self, db: SequenceDatabase, **kwargs: Any
    ) -> list[WorkflowCandidate]:
        """Convenience wrapper for a pre-built SequenceDatabase."""
        return self.discover_patterns(
            sequences=db.sequences,
            session_ids=db.session_ids,
            session_timestamps=db.session_timestamps,
            **kwargs,
        )

    def discover_from_storage(
        self, storage: Any, min_session_length: int = 2, **kwargs: Any
    ) -> list[WorkflowCandidate]:
        """Load sessions from StorageService and run discovery."""
        db = SequenceDatabase.from_storage(storage).filter_min_length(min_session_length)
        logger.info("Loaded %d sessions from storage", len(db))
        return self.discover_from_database(db, **kwargs)

    # ── Filtered queries ──────────────────────────────────────────────────────

    def get_top_workflows(
        self, candidates: list[WorkflowCandidate], n: int = 5
    ) -> list[WorkflowCandidate]:
        return sorted(candidates, key=lambda c: c.rank_score, reverse=True)[:n]

    def get_high_confidence_workflows(
        self, candidates: list[WorkflowCandidate], min_confidence: float = 0.7
    ) -> list[WorkflowCandidate]:
        return [c for c in candidates if c.confidence >= min_confidence]

    def get_high_value_workflows(
        self, candidates: list[WorkflowCandidate], min_value: float = 5.0
    ) -> list[WorkflowCandidate]:
        return [c for c in candidates if c.automation_value_score >= min_value]

    # ── Storage persistence ───────────────────────────────────────────────────

    def persist(self, candidates: list[WorkflowCandidate], storage: Any) -> int:
        """Write candidates to the WorkflowCandidateRepository. Returns saved count."""
        from ghostflow.storage.models.workflow_candidate import (
            WorkflowCandidate as StorageCandidate,
        )

        saved = 0
        for cand in candidates:
            try:
                sc = StorageCandidate.new(
                    event_sequence=cand.sequence,
                    confidence=cand.confidence,
                    frequency=cand.frequency,
                    name=cand.name,
                    status="candidate",
                )
                sc.candidate_id = cand.candidate_id
                sc.first_seen_at = cand.first_seen_at
                sc.last_seen_at = cand.last_seen_at
                storage.candidates.insert_candidate(sc)
                saved += 1
            except Exception as exc:
                logger.warning("Failed to persist candidate %s: %s", cand.candidate_id, exc)
        return saved

    # ── Benchmark ─────────────────────────────────────────────────────────────

    def benchmark(self, n_sessions: int = 1000) -> dict[str, Any]:
        """Quick synthetic benchmark to verify performance SLA."""
        import random

        events = [
            "file_created",
            "file_modified",
            "file_deleted",
            "file_moved",
            "folder_created",
            "folder_deleted",
        ]
        pattern = ["file_created", "file_modified", "file_moved"]
        sequences = []
        for i in range(n_sessions):
            seq = list(pattern) if random.random() < 0.6 else []
            # Add 1-5 random events
            for _ in range(random.randint(1, 5)):
                pos = random.randint(0, len(seq))
                seq.insert(pos, random.choice(events))
            sequences.append(seq)

        t0 = time.monotonic()
        candidates = self.discover_patterns(sequences, top_k=10)
        elapsed = time.monotonic() - t0

        return {
            "sessions": n_sessions,
            "candidates_found": len(candidates),
            "elapsed_seconds": round(elapsed, 3),
            "within_sla": elapsed < 30.0,
        }
