"""RecommendationService — top-level engine that produces personalized picks."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import anthropic

from ghostflow.recommendation.scorer import ScoredIdea, score_ideas
from ghostflow.recommendation.taste_learner import TasteLearner
from ghostflow.storage.models.user_profile import UserProfile
from ghostflow.storage.storage_service import StorageService

logger = logging.getLogger(__name__)

_EXPLAIN_SYSTEM = """You are BuildNext, a project idea advisor for developers.
Given a developer's profile and a shortlist of candidate project ideas,
pick the 3 best matches and explain why each fits this specific person.

Return ONLY valid JSON as a list of exactly 3 objects:
[
  {
    "idea_id": "...",
    "why": "One sentence explaining why this fits THIS developer specifically (max 100 chars)"
  },
  ...
]

Be specific about the person's skills/interests — don't write generic reasons.
"""


@dataclass
class Recommendation:
    idea_id: str
    extracted_title: str
    description: str
    stack: list[str]
    complexity: str
    domain: str
    source_url: str
    trending_score: float
    why: str  # Claude's personalised explanation


@dataclass
class RecommendationResult:
    user_id: str
    picks: list[Recommendation]
    generated_at: str
    candidates_considered: int


class RecommendationService:
    """Produces the weekly 3-pick recommendation for a user.

    Usage::

        svc = RecommendationService(storage)
        result = svc.recommend(user_id="u1", top_n=3)
    """

    def __init__(
        self,
        storage: StorageService,
        api_key: str | None = None,
        model: str = "claude-haiku-4-5",
        days_back: int = 7,
        candidate_pool: int = 15,
    ) -> None:
        self._storage = storage
        self._client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""))
        self._model = model
        self._days_back = days_back
        self._candidate_pool = candidate_pool
        self._learner = TasteLearner(storage)

    def recommend(self, user_id: str, top_n: int = 3) -> RecommendationResult | None:
        """Generate personalised recommendations for a user."""
        profile = self._storage.user_profiles.get_profile(user_id)
        if not profile:
            logger.error("No profile found for user_id=%s", user_id)
            return None

        # 1. Fetch unseen ideas from the last N days
        since = (datetime.now(tz=UTC) - timedelta(days=self._days_back)).isoformat()
        unseen = self._storage.ideas.list_unseen_by_user(user_id=user_id, since=since, limit=50)

        if not unseen:
            logger.info("No new unseen ideas for user=%s", user_id)
            return RecommendationResult(
                user_id=user_id,
                picks=[],
                generated_at=datetime.now(tz=UTC).isoformat(),
                candidates_considered=0,
            )

        # 2. Score and rank locally — take top candidate_pool for Claude
        scored = score_ideas(unseen, profile)
        candidates = scored[: self._candidate_pool]

        # 3. Claude picks the best 3 and explains why
        picks_data = self._claude_pick(profile, candidates, top_n)

        # 4. Build Recommendation objects and mark ideas as seen
        picks: list[Recommendation] = []
        for item in picks_data:
            idea_id = item.get("idea_id", "")
            idea = self._storage.ideas.get_idea(idea_id)
            if not idea:
                continue
            picks.append(
                Recommendation(
                    idea_id=idea_id,
                    extracted_title=idea.extracted_title,
                    description=idea.description,
                    stack=idea.stack,
                    complexity=idea.complexity,
                    domain=idea.domain,
                    source_url=idea.source_url,
                    trending_score=idea.trending_score,
                    why=item.get("why", ""),
                )
            )
            self._learner.on_seen(user_id, idea_id)

        return RecommendationResult(
            user_id=user_id,
            picks=picks,
            generated_at=datetime.now(tz=UTC).isoformat(),
            candidates_considered=len(candidates),
        )

    def on_liked(self, user_id: str, idea_id: str) -> None:
        self._learner.on_liked(user_id, idea_id)

    def on_dismissed(self, user_id: str, idea_id: str) -> None:
        self._learner.on_dismissed(user_id, idea_id)

    def _claude_pick(
        self,
        profile: UserProfile,
        candidates: list[ScoredIdea],
        top_n: int,
    ) -> list[dict[str, Any]]:
        """Ask Claude to pick the best top_n ideas and explain why."""
        profile_text = (
            f"Name: {profile.name}\n"
            f"Skills: {', '.join(profile.skills)}\n"
            f"Interests: {', '.join(profile.interests)}\n"
            f"Experience: {profile.experience}\n"
            f"Goals: {', '.join(profile.goals)}"
        )

        ideas_text = "\n".join(
            f"- idea_id={s.idea.idea_id} | {s.idea.extracted_title} | "
            f"stack={s.idea.stack} | domain={s.idea.domain} | "
            f"complexity={s.idea.complexity} | score={s.final_score:.2f}\n"
            f"  {s.idea.description}"
            for s in candidates
        )

        user_msg = (
            f"Developer profile:\n{profile_text}\n\n"
            f"Candidate ideas (pre-ranked by relevance):\n{ideas_text}\n\n"
            f"Pick the {top_n} best ideas for this developer and explain why each fits them."
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=500,
            system=_EXPLAIN_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        return json.loads(text)
