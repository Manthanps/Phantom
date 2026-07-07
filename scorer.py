"""Scorer — ranks ideas against a user profile before sending to Claude."""

from __future__ import annotations

from dataclasses import dataclass

from ghostflow.storage.models.idea import StoredIdea
from ghostflow.storage.models.user_profile import UserProfile


@dataclass
class ScoredIdea:
    idea: StoredIdea
    relevance_score: float  # 0–1: how well it matches user skills/interests
    final_score: float  # relevance × trending × novelty


def score_ideas(
    ideas: list[StoredIdea],
    profile: UserProfile,
) -> list[ScoredIdea]:
    """Score and rank ideas for a specific user profile.

    Final score = relevance_score × trending_score × novelty_score
    - relevance: overlap between idea stack/domain and user skills/interests
    - trending: normalised upvotes/stars from ingestion (0–1)
    - novelty: set at extraction; penalises oversaturated domains
    """
    # Build lowercase sets for fast lookup
    user_skills = {s.lower() for s in profile.skills}
    user_interests = {i.lower() for i in profile.interests}
    liked_domains = _liked_domains(profile)

    scored: list[ScoredIdea] = []
    for idea in ideas:
        if not idea.extracted_title or idea.extracted_title == "[not-a-project]":
            continue

        relevance = _relevance(idea, user_skills, user_interests, liked_domains)
        final = relevance * idea.trending_score * idea.novelty_score

        scored.append(ScoredIdea(idea=idea, relevance_score=relevance, final_score=final))

    # Sort descending by final score
    scored.sort(key=lambda s: s.final_score, reverse=True)
    return scored


def _relevance(
    idea: StoredIdea,
    user_skills: set[str],
    user_interests: set[str],
    liked_domains: dict[str, float],
) -> float:
    score = 0.0

    # Stack overlap — each matching technology adds 0.15 (capped at 0.45)
    idea_stack = {s.lower() for s in idea.stack}
    stack_overlap = len(idea_stack & user_skills)
    score += min(stack_overlap * 0.15, 0.45)

    # Domain matches an interest
    if idea.domain and idea.domain.lower() in user_interests:
        score += 0.30

    # Domain appears in liked history (taste learning)
    domain_boost = liked_domains.get(idea.domain or "", 0.0)
    score += min(domain_boost, 0.25)

    # Complexity match
    score += _complexity_fit(idea.complexity)

    return min(score, 1.0)


def _complexity_fit(complexity: str) -> float:
    """Small bonus — idea complexity is acceptable (not always 'advanced')."""
    return 0.10 if complexity in ("beginner", "intermediate") else 0.05


def _liked_domains(profile: UserProfile) -> dict[str, float]:
    """Extract domain preference weights from the stored preferences dict.

    The memory layer writes these via update_preferences() after likes/dismisses.
    Format: preferences["domain_weights"] = {"devtools": 0.8, "ai": 0.5, ...}
    """
    return profile.preferences.get("domain_weights", {})
