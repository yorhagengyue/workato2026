#!/usr/bin/env python3
"""Heuristic scoring for candidate signals.

Purpose: replace fixed ingest scores with deterministic, explainable scoring.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _tokenize(text: str) -> set[str]:
    tokens = [t.strip(" ,.:;!?()[]{}<>\n\t\"").lower() for t in text.split()]
    return {t for t in tokens if t}


def _overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, len(left | right))


def score_candidate(candidate: dict[str, Any], project_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a copy of candidate with recalculated score fields."""

    scored = dict(candidate)

    summary = str(scored.get("summary", ""))
    source_type = str(scored.get("source_type", ""))
    source_class = str(scored.get("source_class", "A"))
    evidence_grade = str(scored.get("evidence_grade", "A0"))
    change_types = scored.get("claimed_change_type", [])
    if not isinstance(change_types, list):
        change_types = []

    published = _parse_dt(scored.get("published_at"))
    now = datetime.now(timezone.utc)
    age_days = (now - published).days if published else 30

    stack_tokens = set()
    goal_tokens = set()
    if isinstance(project_snapshot, dict):
        stack_tokens = _tokenize(" ".join(project_snapshot.get("tech_stack", [])))
        goal_tokens = _tokenize(" ".join(project_snapshot.get("current_goals", [])))

    candidate_tokens = _tokenize(summary + " " + " ".join(scored.get("affected_stack", [])))

    # Context similarity: lexical overlap with stack/goals.
    context_similarity = _clamp(0.6 * _overlap_ratio(candidate_tokens, stack_tokens) + 0.4 * _overlap_ratio(candidate_tokens, goal_tokens))

    # Relevance: context + boost for high-impact change types.
    change_boost = 0.0
    if "security" in change_types:
        change_boost += 0.12
    if "breaking" in change_types:
        change_boost += 0.10
    if "feature" in change_types:
        change_boost += 0.06
    relevance_score = _clamp(0.55 * context_similarity + 0.25 + change_boost)

    # Novelty decays with age.
    novelty_score = _clamp(1.0 - min(age_days / 60.0, 1.0))

    # Impact based on change types and summary cues.
    impact_score = 0.35
    if "security" in change_types:
        impact_score += 0.25
    if "breaking" in change_types:
        impact_score += 0.2
    if "perf" in change_types:
        impact_score += 0.1
    if any(k in summary.lower() for k in ["migration", "deprecated", "auth", "compatibility"]):
        impact_score += 0.08
    impact_score = _clamp(impact_score)

    # Trust from source and evidence.
    trust_score = 0.5
    if source_type in {"official_doc", "official_blog"}:
        trust_score += 0.3
    if source_type == "github":
        trust_score += 0.2
    if source_class == "A":
        trust_score += 0.1
    if evidence_grade == "A2":
        trust_score += 0.08
    if evidence_grade == "A1":
        trust_score += 0.04
    trust_score = _clamp(trust_score)

    # Noise risk from opinion-like content and source class.
    noise_risk_score = 0.15
    if source_class == "B":
        noise_risk_score += 0.35
    if "opinion" in change_types:
        noise_risk_score += 0.2
    if any(k in summary.lower() for k in ["thread", "hot take", "rumor", "speculation"]):
        noise_risk_score += 0.15
    noise_risk_score = _clamp(noise_risk_score)

    # Execution cost from content size and complexity markers.
    execution_cost_score = 0.2
    execution_cost_score += min(len(summary) / 1200.0, 0.3)
    if any(k in summary.lower() for k in ["migration", "refactor", "breaking"]):
        execution_cost_score += 0.2
    execution_cost_score = _clamp(execution_cost_score)

    # Total score in [0,100].
    score_total = round(
        100
        * (
            0.26 * relevance_score
            + 0.18 * context_similarity
            + 0.16 * impact_score
            + 0.14 * trust_score
            + 0.10 * novelty_score
            + 0.08 * (1.0 - noise_risk_score)
            + 0.08 * (1.0 - execution_cost_score)
        ),
        2,
    )

    scored.update(
        {
            "relevance_score": round(relevance_score, 4),
            "context_similarity": round(context_similarity, 4),
            "novelty_score": round(novelty_score, 4),
            "impact_score": round(impact_score, 4),
            "trust_score": round(trust_score, 4),
            "noise_risk_score": round(noise_risk_score, 4),
            "execution_cost_score": round(execution_cost_score, 4),
            "score_total": score_total,
        }
    )
    return scored
