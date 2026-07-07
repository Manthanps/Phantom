"""Sequence similarity — overlap coefficient on event-type bigrams."""

from __future__ import annotations


def bigrams(seq: list[str]) -> set[tuple[str, str]]:
    """Return the set of consecutive 2-grams from *seq*."""
    if len(seq) < 2:
        return set()
    return {(seq[i], seq[i + 1]) for i in range(len(seq) - 1)}


def unigrams(seq: list[str]) -> set[str]:
    return set(seq)


def overlap_coefficient(seq_a: list[str], seq_b: list[str]) -> float:
    """
    Overlap coefficient on event-type bigrams.

    Bigrams capture sequential structure (order matters), not just set membership.
    Falls back to unigram overlap for singleton sequences (length == 1).

    Returns a float in [0.0, 1.0]:
    - 0.0 → completely different
    - 1.0 → one sequence's bigrams are a subset of the other's
    """
    bg_a = bigrams(seq_a)
    bg_b = bigrams(seq_b)

    if not bg_a or not bg_b:
        # Fallback: unigram overlap for very short sequences
        ug_a = unigrams(seq_a)
        ug_b = unigrams(seq_b)
        if not ug_a or not ug_b:
            return 0.0
        return len(ug_a & ug_b) / min(len(ug_a), len(ug_b))

    intersection = len(bg_a & bg_b)
    return intersection / min(len(bg_a), len(bg_b))


def jaccard(seq_a: list[str], seq_b: list[str]) -> float:
    """Jaccard similarity on event-type unigrams (set overlap, ignores order)."""
    a = set(seq_a)
    b = set(seq_b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
