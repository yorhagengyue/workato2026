#!/usr/bin/env python3
"""Decision engine for attention triage and controlled action handoff.

This module enforces the fixed gate order:
Evidence -> Context -> Profile -> Policy -> Action
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import validator

GATE_ORDER = [
    "Evidence Gate",
    "Context Gate",
    "Profile Gate",
    "Policy Gate",
    "Action Gate",
]

DECISION_LEVELS = ["discard", "mention", "hint", "deep_read", "action"]


def _degrade(decision: str) -> str:
    idx = DECISION_LEVELS.index(decision)
    return DECISION_LEVELS[max(0, idx - 1)]


def _promote(decision: str) -> str:
    idx = DECISION_LEVELS.index(decision)
    return DECISION_LEVELS[min(len(DECISION_LEVELS) - 1, idx + 1)]


def _add_reason(result: dict[str, Any], reason: str) -> None:
    if reason not in result["decision_reason"]:
        result["decision_reason"].append(reason)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value)


def _contains_any(haystack: str, tokens: list[str]) -> bool:
    haystack_lower = haystack.lower()
    return any(token.lower() in haystack_lower for token in tokens if isinstance(token, str) and token.strip())


def _profile_adjustment(candidate: dict[str, Any], project_snapshot: dict[str, Any] | None) -> str:
    if not isinstance(project_snapshot, dict):
        return "none"

    acceptance = project_snapshot.get("acceptance_signals", [])
    rejection = project_snapshot.get("rejection_signals", [])
    current_goals = project_snapshot.get("current_goals", [])

    haystack = " ".join(
        [
            _normalize_text(candidate.get("summary")),
            _normalize_text(candidate.get("affected_stack")),
            _normalize_text(candidate.get("claimed_change_type")),
            _normalize_text(candidate.get("source_type")),
        ]
    )

    if _contains_any(haystack, rejection):
        return "degrade"

    if _contains_any(haystack, acceptance) or _contains_any(haystack, current_goals):
        return "boost"

    return "none"


def _invalid_result(candidate: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    trace_id = candidate.get("trace_id") if isinstance(candidate, dict) else ""
    return {
        "decision": "discard",
        "decision_reason": ["INVALID_CANDIDATE_PAYLOAD"],
        "evidence_grade": candidate.get("evidence_grade", "A0") if isinstance(candidate, dict) else "A0",
        "relevance_score": float(candidate.get("relevance_score", 0.0)) if isinstance(candidate, dict) and isinstance(candidate.get("relevance_score"), (int, float)) else 0.0,
        "noise_risk_score": float(candidate.get("noise_risk_score", 1.0)) if isinstance(candidate, dict) and isinstance(candidate.get("noise_risk_score"), (int, float)) else 1.0,
        "requires_user_confirm": False,
        "trace_id": trace_id if isinstance(trace_id, str) else "",
        "gate_path": ["Validation"],
        "validation_errors": errors,
    }


def decide_candidate(
    candidate: dict[str, Any],
    project_snapshot: dict[str, Any] | None = None,
    *,
    linked_a_evidence: bool = False,
    user_interest: bool = False,
    requested_stage: str = "triage",
    deep_read_completed: bool = False,
    user_confirmed: bool = False,
    strict_validation: bool = False,
) -> dict[str, Any]:
    """Evaluate one candidate and return an auditable decision packet."""

    if strict_validation:
        validation_errors = validator.validate_repo_compare(candidate)
        if validation_errors:
            return _invalid_result(candidate, validation_errors)

    if requested_stage not in {"triage", "action"}:
        raise ValueError("requested_stage must be triage or action")

    result: dict[str, Any] = {
        "decision": "discard",
        "decision_reason": [],
        "evidence_grade": candidate.get("evidence_grade", "A0"),
        "relevance_score": float(candidate.get("relevance_score", 0.0)),
        "noise_risk_score": float(candidate.get("noise_risk_score", 0.0)),
        "requires_user_confirm": False,
        "trace_id": candidate.get("trace_id", ""),
        "gate_path": [],
        "validation_errors": [],
    }

    source_class = candidate.get("source_class")
    evidence_grade = candidate.get("evidence_grade", "A0")
    relevance_score = float(candidate.get("relevance_score", 0.0))
    noise_risk_score = float(candidate.get("noise_risk_score", 0.0))
    security_gate = candidate.get("security_gate", "pass")

    tentative_decision = "hint"
    profile_boosted = False

    # 1) Evidence Gate
    result["gate_path"].append(GATE_ORDER[0])
    if source_class == "B" and not linked_a_evidence:
        result["decision"] = "mention"
        _add_reason(result, "B_WITHOUT_A_EVIDENCE")
        return result

    if source_class not in {"A", "B"}:
        result["decision"] = "discard"
        _add_reason(result, "INVALID_SOURCE_CLASS")
        return result

    _add_reason(result, "EVIDENCE_PASS")

    # 2) Context Gate
    result["gate_path"].append(GATE_ORDER[1])
    if relevance_score < 0.45:
        result["decision"] = "discard"
        _add_reason(result, "LOW_CONTEXT_RELEVANCE")
        return result

    if relevance_score <= 0.75:
        tentative_decision = "hint"
        _add_reason(result, "MID_CONTEXT_RELEVANCE")
    else:
        if source_class == "A" and evidence_grade in {"A1", "A2"}:
            tentative_decision = "deep_read"
        else:
            tentative_decision = "hint"
        _add_reason(result, "HIGH_CONTEXT_RELEVANCE")

    # 3) Profile Gate
    result["gate_path"].append(GATE_ORDER[2])
    adjustment = _profile_adjustment(candidate, project_snapshot)
    if adjustment == "degrade":
        tentative_decision = _degrade(tentative_decision)
        _add_reason(result, "PROFILE_MISMATCH")
    elif adjustment == "boost":
        _add_reason(result, "PROFILE_MATCH")
        # Controlled one-level promotion:
        # only A-source with >=A1 evidence and reasonably high relevance can be promoted.
        if (
            source_class == "A"
            and evidence_grade in {"A1", "A2"}
            and relevance_score >= 0.70
            and tentative_decision in {"mention", "hint"}
        ):
            tentative_decision = _promote(tentative_decision)
            profile_boosted = True
            _add_reason(result, "PROFILE_MATCH_BOOST")

    # 4) Policy Gate
    result["gate_path"].append(GATE_ORDER[3])
    if security_gate == "block":
        result["decision"] = "discard"
        _add_reason(result, "POLICY_BLOCK")
        return result

    if noise_risk_score >= 0.8:
        tentative_decision = _degrade(tentative_decision)
        _add_reason(result, "HIGH_NOISE_RISK")

    # 5) Action Gate
    result["gate_path"].append(GATE_ORDER[4])
    decision = tentative_decision

    if tentative_decision == "deep_read":
        deep_read_rule_a = source_class == "A" and (relevance_score > 0.75 or profile_boosted) and security_gate == "pass"
        deep_read_rule_b = source_class == "A" and user_interest

        if deep_read_rule_a:
            _add_reason(result, "DEEP_READ_RULE_A")
            decision = "deep_read"
        elif deep_read_rule_b:
            _add_reason(result, "DEEP_READ_RULE_B")
            decision = "deep_read"
        else:
            decision = "hint"
            _add_reason(result, "DEEP_READ_THRESHOLD_NOT_MET")

    if requested_stage == "action":
        if decision != "deep_read":
            _add_reason(result, "ACTION_STAGE_REQUIRES_DEEP_READ")
        elif not deep_read_completed:
            _add_reason(result, "ACTION_NEEDS_DEEP_READ_OUTPUT")
        elif not user_confirmed:
            _add_reason(result, "ACTION_NEEDS_CONFIRM")
        else:
            decision = "action"
            _add_reason(result, "ACTION_CONFIRMED")

    result["decision"] = decision
    result["requires_user_confirm"] = decision in {"deep_read", "action"}
    return result


def build_handoff_payload(candidate: dict[str, Any], decision_packet: dict[str, Any]) -> dict[str, Any]:
    """Create a minimal central->Workato payload."""
    return {
        "candidate_id": candidate.get("candidate_id", ""),
        "project_id": candidate.get("project_id", ""),
        "decision": decision_packet["decision"],
        "decision_reason": decision_packet["decision_reason"],
        "requires_user_confirm": decision_packet["requires_user_confirm"],
        "source_class": candidate.get("source_class", ""),
        "source_type": candidate.get("source_type", ""),
        "security_gate": candidate.get("security_gate", ""),
        "trace_id": decision_packet.get("trace_id", ""),
    }


def build_audit_event(
    decision_packet: dict[str, Any],
    *,
    who: str,
    source: str,
    trigger_reason: list[str] | None = None,
    files_accessed: list[str] | None = None,
    action_taken: str | None = None,
    user_confirmed: bool = False,
    event_time: str | None = None,
) -> dict[str, Any]:
    """Build one audit event that fits tbl_audit_events fields."""

    when = event_time or datetime.now(timezone.utc).isoformat()
    return {
        "who": who,
        "when": when,
        "source": source,
        "trigger_reason": trigger_reason or decision_packet.get("decision_reason", []),
        "files_accessed": files_accessed or [],
        "action_taken": action_taken or decision_packet.get("decision", ""),
        "user_confirmed": user_confirmed,
        "trace_id": decision_packet.get("trace_id", ""),
    }


def _validate_handoff_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "candidate_id",
        "project_id",
        "decision",
        "decision_reason",
        "requires_user_confirm",
        "source_class",
        "source_type",
        "security_gate",
        "trace_id",
    }
    missing = required - payload.keys()
    if missing:
        errors.append(f"missing_required={sorted(missing)}")

    if payload.get("decision") not in {"discard", "mention", "hint", "deep_read", "action"}:
        errors.append("decision invalid")
    if not isinstance(payload.get("decision_reason"), list):
        errors.append("decision_reason must be list")
    if not isinstance(payload.get("requires_user_confirm"), bool):
        errors.append("requires_user_confirm must be bool")
    if payload.get("source_class") not in {"A", "B"}:
        errors.append("source_class invalid")
    if payload.get("security_gate") not in {"pass", "review", "block"}:
        errors.append("security_gate invalid")
    if not isinstance(payload.get("trace_id"), str) or not payload.get("trace_id", "").strip():
        errors.append("trace_id invalid")

    return errors


def persist_handoff_payload(payload: dict[str, Any], outbox_path: str = "output/workato-outbox/handoff.jsonl") -> dict[str, Any]:
    """Persist a validated handoff payload to outbox for Workato ingestion."""
    errors = _validate_handoff_payload(payload)
    if errors:
        raise ValueError(f"invalid handoff payload: {errors}")

    path = Path(outbox_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return {"outbox_path": str(path), "trace_id": payload["trace_id"]}


def persist_audit_event(event: dict[str, Any], audit_path: str = "output/audit/tbl_audit_events.jsonl") -> dict[str, Any]:
    """Persist one audit event record."""
    required = {"who", "when", "source", "trigger_reason", "files_accessed", "action_taken", "user_confirmed", "trace_id"}
    missing = required - event.keys()
    if missing:
        raise ValueError(f"invalid audit event, missing={sorted(missing)}")

    path = Path(audit_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return {"audit_path": str(path), "trace_id": event["trace_id"]}
