"""TasteLearner — updates user preference weights from likes and dismisses."""

from __future__ import annotations

import logging

from ghostflow.storage.storage_service import StorageService

logger = logging.getLogger(__name__)

_LIKE_BOOST = 0.15
_DISMISS_PENALTY = 0.10
_MAX_WEIGHT = 1.0
_MIN_WEIGHT = 0.0
_NEUTRAL_WEIGHT = 0.5
_DEFAULT_DECAY_RATE = 0.05


class TasteLearner:
    """Adjusts domain_weights in user preferences based on feedback.

    Likes increase domain weight; dismisses decrease it. Weights stay in
    [0, 1] and can be decayed toward the neutral 0.5 over time via ``decay()``
    so stale preferences fade when a user's taste is no longer reinforced.

    Usage::

        learner = TasteLearner(storage)
        learner.on_liked(user_id="u1", idea_id="abc")
        learner.on_dismissed(user_id="u1", idea_id="xyz")
        learner.decay(user_id="u1")   # nudge all weights back toward 0.5
    """

    def __init__(self, storage: StorageService) -> None:
        self._storage = storage

    def on_liked(self, user_id: str, idea_id: str) -> None:
        self._storage.memory.mark_liked(user_id, idea_id)
        idea = self._storage.ideas.get_idea(idea_id)
        if idea and idea.domain:
            self._adjust_domain(user_id, idea.domain, _LIKE_BOOST)
            logger.info("Liked domain=%s user=%s boost=%.2f", idea.domain, user_id, _LIKE_BOOST)

    def on_dismissed(self, user_id: str, idea_id: str) -> None:
        self._storage.memory.mark_dismissed(user_id, idea_id)
        idea = self._storage.ideas.get_idea(idea_id)
        if idea and idea.domain:
            self._adjust_domain(user_id, idea.domain, -_DISMISS_PENALTY)
            logger.info(
                "Dismissed domain=%s user=%s penalty=%.2f", idea.domain, user_id, _DISMISS_PENALTY
            )

    def on_seen(self, user_id: str, idea_id: str) -> None:
        self._storage.memory.mark_seen(user_id, idea_id)

    def decay(self, user_id: str, rate: float = _DEFAULT_DECAY_RATE) -> None:
        """Pull every domain weight a fraction of the way back toward 0.5.

        Applied periodically (e.g. once per recommendation cycle), this lets
        preferences that are no longer reinforced by likes/dismisses fade back
        toward neutral. ``rate`` is the fraction of the remaining distance to
        0.5 removed per call, clamped to [0, 1] (0 = no decay, 1 = reset).
        """
        rate = max(0.0, min(1.0, rate))
        if rate == 0.0:
            return
        profile = self._storage.user_profiles.get_profile(user_id)
        if not profile:
            return
        weights: dict[str, float] = dict(profile.preferences.get("domain_weights", {}))
        if not weights:
            return
        decayed = {
            domain: round(w + (_NEUTRAL_WEIGHT - w) * rate, 3) for domain, w in weights.items()
        }
        self._storage.user_profiles.update_preferences(user_id, {"domain_weights": decayed})
        logger.info(
            "Decayed %d domain weights toward 0.5 for user=%s (rate=%.2f)",
            len(decayed),
            user_id,
            rate,
        )

    def _adjust_domain(self, user_id: str, domain: str, delta: float) -> None:
        profile = self._storage.user_profiles.get_profile(user_id)
        if not profile:
            return
        weights: dict[str, float] = dict(profile.preferences.get("domain_weights", {}))
        current = weights.get(domain, 0.5)
        weights[domain] = round(max(_MIN_WEIGHT, min(_MAX_WEIGHT, current + delta)), 3)
        self._storage.user_profiles.update_preferences(user_id, {"domain_weights": weights})
