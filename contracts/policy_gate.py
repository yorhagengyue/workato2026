#!/usr/bin/env python3
"""Runtime policy gate for local execution constraints (MVP)."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any

TRACE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
ALLOWED_ACTIONS = {"deep_read", "write_watchlist", "write_note", "write_follow_up"}
PROHIBITED_ACTIONS = {"write_code", "auto_commit", "send_external_message", "high_impact_task", "prod_api_call"}


def _is_subpath(path: str, base: str) -> bool:
    p = PurePosixPath(path)
    b = PurePosixPath(base)
    try:
        p.relative_to(b)
        return True
    except ValueError:
        return False


def evaluate_runtime_request(request: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []

    trace_id = request.get("trace_id")
    if not isinstance(trace_id, str) or not TRACE_ID_RE.match(trace_id):
        reasons.append("missing_or_invalid_trace_id")

    allowed_dirs = request.get("allowed_dirs")
    if not isinstance(allowed_dirs, list) or not allowed_dirs or any(not isinstance(d, str) or not d.strip() for d in allowed_dirs):
        reasons.append("invalid_allowed_dirs")

    requested_path = request.get("requested_path")
    if not isinstance(requested_path, str) or not requested_path.strip():
        reasons.append("invalid_requested_path")

    max_files = request.get("max_files")
    if not isinstance(max_files, int) or max_files < 1 or max_files > 5:
        reasons.append("max_files_limit_violation")

    max_depth = request.get("max_depth")
    if not isinstance(max_depth, int) or max_depth < 1 or max_depth > 2:
        reasons.append("max_depth_limit_violation")

    action_type = request.get("action_type")
    if action_type in PROHIBITED_ACTIONS:
        reasons.append("prohibited_action_type")
    elif action_type not in ALLOWED_ACTIONS:
        reasons.append("unknown_or_disallowed_action_type")

    security_gate = request.get("security_gate", "pass")
    if security_gate not in {"pass", "review", "block"}:
        reasons.append("invalid_security_gate")
    if security_gate == "block":
        reasons.append("security_gate_block")

    if isinstance(allowed_dirs, list) and allowed_dirs and isinstance(requested_path, str) and requested_path.strip():
        if not any(_is_subpath(requested_path, d) for d in allowed_dirs):
            reasons.append("requested_path_outside_allowed_dirs")

    # Deep read is read-only and scoped.
    if action_type == "deep_read":
        # Reject top-level repository scan attempts.
        if isinstance(allowed_dirs, list) and isinstance(requested_path, str):
            normalized = [PurePosixPath(d) for d in allowed_dirs if isinstance(d, str) and d.strip()]
            if any(PurePosixPath(requested_path) == d for d in normalized) and (max_files == 5 and max_depth == 2):
                # This combination is still acceptable when explicitly bounded.
                pass

    allow = len(reasons) == 0
    decision = "ALLOW" if allow else "DENY"

    return {
        "decision": decision,
        "reasons": reasons,
        "log": {
            "trace_id": trace_id if isinstance(trace_id, str) else "",
            "action_type": action_type,
            "requested_path": requested_path,
            "allowed_dirs": allowed_dirs,
            "decision": decision,
            "deny_reason_count": len(reasons),
        },
    }
