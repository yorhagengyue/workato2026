#!/usr/bin/env python3
"""Contract validator for Day 1.

Usage:
  python contracts/validator.py project_snapshot path/to/payload.json
  python contracts/validator.py repo_compare path/to/payload.json
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

TRACE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")

PROJECT_REQUIRED = {
    "project_id",
    "snapshot_time",
    "repo_urls",
    "tech_stack",
    "active_modules",
    "current_goals",
    "open_problems",
    "non_goals",
    "risk_tolerance",
    "latency_budget_ms",
    "cost_budget_daily_usd",
    "security_constraints",
    "acceptance_signals",
    "rejection_signals",
    "trace_id",
    "last_feedback",
}

REPO_REQUIRED = {
    "candidate_id",
    "source_class",
    "source_type",
    "evidence_grade",
    "candidate_url",
    "published_at",
    "summary",
    "claimed_change_type",
    "affected_stack",
    "relevance_score",
    "context_similarity",
    "novelty_score",
    "impact_score",
    "trust_score",
    "noise_risk_score",
    "execution_cost_score",
    "score_total",
    "decision",
    "decision_reason",
    "trigger_reason",
    "requires_user_confirm",
    "security_gate",
    "trace_id",
}


def _is_iso_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _is_non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)


def _num_range(value: Any, min_v: float, max_v: float) -> bool:
    return isinstance(value, (int, float)) and min_v <= float(value) <= max_v


def _is_http_url(value: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_project_snapshot(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing = PROJECT_REQUIRED - payload.keys()
    extra = payload.keys() - PROJECT_REQUIRED
    if missing:
        errors.append(f"missing_required={sorted(missing)}")
    if extra:
        errors.append(f"unexpected_fields={sorted(extra)}")

    if not isinstance(payload.get("project_id"), str) or not payload.get("project_id", "").strip():
        errors.append("project_id must be non-empty string")
    if not isinstance(payload.get("snapshot_time"), str) or not _is_iso_datetime(payload["snapshot_time"]):
        errors.append("snapshot_time must be ISO datetime")

    for key in [
        "repo_urls",
        "tech_stack",
        "active_modules",
        "current_goals",
        "open_problems",
        "non_goals",
        "security_constraints",
        "acceptance_signals",
        "rejection_signals",
    ]:
        if key in payload and not _is_non_empty_string_list(payload[key]):
            errors.append(f"{key} must be list[str non-empty]")

    if isinstance(payload.get("repo_urls"), list):
        invalid_repo_urls = [u for u in payload["repo_urls"] if not _is_http_url(u)]
        if invalid_repo_urls:
            errors.append(f"repo_urls must contain valid http/https URLs: {invalid_repo_urls}")

    if payload.get("risk_tolerance") not in {"low", "medium", "high"}:
        errors.append("risk_tolerance must be low|medium|high")

    if not isinstance(payload.get("latency_budget_ms"), int) or payload["latency_budget_ms"] < 0:
        errors.append("latency_budget_ms must be integer >= 0")

    cbd = payload.get("cost_budget_daily_usd")
    if not isinstance(cbd, (int, float)) or float(cbd) < 0:
        errors.append("cost_budget_daily_usd must be number >= 0")

    trace_id = payload.get("trace_id")
    if not isinstance(trace_id, str) or not TRACE_ID_RE.match(trace_id):
        errors.append("trace_id format invalid")

    last_feedback = payload.get("last_feedback")
    if not isinstance(last_feedback, list):
        errors.append("last_feedback must be list")
    else:
        for idx, item in enumerate(last_feedback):
            if not isinstance(item, dict):
                errors.append(f"last_feedback[{idx}] must be object")
                continue
            required = {"item_id", "feedback", "reason"}
            miss = required - item.keys()
            extra_item = item.keys() - required
            if miss:
                errors.append(f"last_feedback[{idx}] missing={sorted(miss)}")
            if extra_item:
                errors.append(f"last_feedback[{idx}] unexpected={sorted(extra_item)}")
            if item.get("feedback") not in {"upvote", "downvote", "mute", "act"}:
                errors.append(f"last_feedback[{idx}].feedback invalid")
            if not isinstance(item.get("item_id"), str) or not item.get("item_id", "").strip():
                errors.append(f"last_feedback[{idx}].item_id invalid")
            if not isinstance(item.get("reason"), str) or not item.get("reason", "").strip():
                errors.append(f"last_feedback[{idx}].reason invalid")

    return errors


def validate_repo_compare(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing = REPO_REQUIRED - payload.keys()
    extra = payload.keys() - REPO_REQUIRED
    if missing:
        errors.append(f"missing_required={sorted(missing)}")
    if extra:
        errors.append(f"unexpected_fields={sorted(extra)}")

    if payload.get("source_class") not in {"A", "B"}:
        errors.append("source_class must be A|B")
    if payload.get("source_type") not in {"github", "official_doc", "official_blog", "tweet_whitelist"}:
        errors.append("source_type invalid")
    if payload.get("evidence_grade") not in {"A0", "A1", "A2"}:
        errors.append("evidence_grade must be A0|A1|A2")

    if not isinstance(payload.get("published_at"), str) or not _is_iso_datetime(payload["published_at"]):
        errors.append("published_at must be ISO datetime")

    if not _is_http_url(payload.get("candidate_url", "")):
        errors.append("candidate_url must be valid http/https URL")

    if not isinstance(payload.get("summary"), str) or not payload.get("summary", "").strip():
        errors.append("summary must be non-empty string")

    cct = payload.get("claimed_change_type")
    valid_change_type = {"feature", "breaking", "security", "perf", "opinion"}
    if not isinstance(cct, list) or not cct or any(v not in valid_change_type for v in cct):
        errors.append("claimed_change_type invalid")

    if not _is_non_empty_string_list(payload.get("affected_stack", [])):
        errors.append("affected_stack must be list[str non-empty]")

    for score_key in [
        "relevance_score",
        "context_similarity",
        "novelty_score",
        "impact_score",
        "trust_score",
        "noise_risk_score",
        "execution_cost_score",
    ]:
        if not _num_range(payload.get(score_key), 0.0, 1.0):
            errors.append(f"{score_key} must be in [0,1]")

    if not _num_range(payload.get("score_total"), 0.0, 100.0):
        errors.append("score_total must be in [0,100]")

    if payload.get("decision") not in {"discard", "mention", "hint", "deep_read", "action"}:
        errors.append("decision invalid")

    if not _is_non_empty_string_list(payload.get("decision_reason", [])):
        errors.append("decision_reason must be list[str non-empty]")

    trigger_reason = payload.get("trigger_reason")
    if not isinstance(trigger_reason, list) or any(not isinstance(v, str) or not v.strip() for v in trigger_reason):
        errors.append("trigger_reason must be list[str non-empty]")

    if not isinstance(payload.get("requires_user_confirm"), bool):
        errors.append("requires_user_confirm must be bool")

    if payload.get("security_gate") not in {"pass", "review", "block"}:
        errors.append("security_gate must be pass|review|block")

    trace_id = payload.get("trace_id")
    if not isinstance(trace_id, str) or not TRACE_ID_RE.match(trace_id):
        errors.append("trace_id format invalid")

    # Contract hard rules (Decision Table + Security Contract)
    decision = payload.get("decision")
    source_class = payload.get("source_class")
    evidence_grade = payload.get("evidence_grade")
    relevance_score = float(payload.get("relevance_score", -1)) if isinstance(payload.get("relevance_score"), (int, float)) else -1
    noise_risk_score = float(payload.get("noise_risk_score", -1)) if isinstance(payload.get("noise_risk_score"), (int, float)) else -1
    security_gate = payload.get("security_gate")

    if source_class == "B" and decision in {"deep_read", "action"}:
        errors.append("contract_violation: B-only candidate cannot deep_read/action")

    if payload.get("source_type") == "tweet_whitelist" and source_class != "B":
        errors.append("contract_violation: source_type=tweet_whitelist requires source_class=B")

    if payload.get("source_type") in {"github", "official_doc", "official_blog"} and source_class != "A":
        errors.append("contract_violation: github/official_* source_type requires source_class=A")

    if security_gate == "block" and decision != "discard":
        errors.append("contract_violation: security_gate=block must produce decision=discard")

    if decision == "action" and payload.get("requires_user_confirm") is not True:
        errors.append("contract_violation: action requires user confirmation")

    if decision in {"deep_read", "action"} and evidence_grade == "A0":
        errors.append("contract_violation: deep_read/action requires evidence_grade >= A1")

    if relevance_score < 0.45 and decision != "discard":
        errors.append("contract_violation: relevance_score < 0.45 must be discard")

    if 0.45 <= relevance_score <= 0.75 and decision in {"deep_read", "action"}:
        errors.append("contract_violation: mid relevance cannot deep_read/action")

    if noise_risk_score >= 0.8 and decision == "action":
        errors.append("contract_violation: high noise risk cannot keep action level")

    return errors


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python contracts/validator.py <project_snapshot|repo_compare> <payload.json>")
        return 2

    schema_name = sys.argv[1].strip()
    payload_path = Path(sys.argv[2])

    if not payload_path.exists():
        print(f"error: file not found: {payload_path}")
        return 2

    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}")
        return 2

    if not isinstance(payload, dict):
        print("error: payload must be an object")
        return 2

    if schema_name == "project_snapshot":
        errors = validate_project_snapshot(payload)
    elif schema_name == "repo_compare":
        errors = validate_repo_compare(payload)
    else:
        print("error: schema must be project_snapshot or repo_compare")
        return 2

    if errors:
        print("INVALID")
        for err in errors:
            print(f"- {err}")
        return 1

    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
