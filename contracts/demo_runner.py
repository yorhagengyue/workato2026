#!/usr/bin/env python3
"""Minimal runnable flow for demo purposes.

Run:
  python contracts/demo_runner.py
"""

from __future__ import annotations

import json
from pathlib import Path

import decision_engine
import policy_gate


def _sample_snapshot() -> dict:
    return {
        "project_id": "proj-demo",
        "snapshot_time": "2026-03-27T10:00:00Z",
        "repo_urls": ["https://github.com/acme/attention"],
        "tech_stack": ["python", "workato"],
        "active_modules": ["decision-engine"],
        "current_goals": ["reduce_interruptions", "safe_actions"],
        "open_problems": ["noise"],
        "non_goals": ["auto_commit"],
        "risk_tolerance": "medium",
        "latency_budget_ms": 1500,
        "cost_budget_daily_usd": 25,
        "security_constraints": ["readonly_default"],
        "acceptance_signals": ["official", "security", "release"],
        "rejection_signals": ["open_twitter_scrape", "auto_commit"],
        "trace_id": "trace.demo.snapshot.0001",
        "last_feedback": [],
    }


def _sample_candidate() -> dict:
    return {
        "candidate_id": "cand-demo-001",
        "project_id": "proj-demo",
        "source_class": "A",
        "source_type": "official_doc",
        "evidence_grade": "A1",
        "candidate_url": "https://example.com/official-release",
        "published_at": "2026-03-27T09:00:00Z",
        "summary": "Official release introduces MCP auth changes.",
        "claimed_change_type": ["security", "feature"],
        "affected_stack": ["mcp", "python"],
        "relevance_score": 0.86,
        "context_similarity": 0.84,
        "novelty_score": 0.65,
        "impact_score": 0.83,
        "trust_score": 0.92,
        "noise_risk_score": 0.2,
        "execution_cost_score": 0.4,
        "score_total": 88,
        "decision": "hint",
        "decision_reason": ["seed"],
        "trigger_reason": ["official release"],
        "requires_user_confirm": False,
        "security_gate": "pass",
        "trace_id": "trace.demo.candidate.0001",
    }


def main() -> int:
    snapshot = _sample_snapshot()
    candidate = _sample_candidate()

    triage = decision_engine.decide_candidate(candidate, snapshot)
    handoff = decision_engine.build_handoff_payload(candidate, triage)

    policy_request = {
        "trace_id": triage["trace_id"],
        "allowed_dirs": ["/workspace/project/src"],
        "requested_path": "/workspace/project/src/runtime",
        "max_files": 3,
        "max_depth": 2,
        "action_type": "deep_read",
        "security_gate": candidate["security_gate"],
    }
    policy = policy_gate.evaluate_runtime_request(policy_request)

    audit = decision_engine.build_audit_event(
        triage,
        who="system",
        source="decision_engine",
        trigger_reason=triage["decision_reason"],
        files_accessed=[],
        action_taken=triage["decision"],
        user_confirmed=False,
    )

    out_dir = Path("output/demo-run")
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "triage.json").write_text(json.dumps(triage, indent=2), encoding="utf-8")
    (out_dir / "handoff.json").write_text(json.dumps(handoff, indent=2), encoding="utf-8")
    (out_dir / "policy.json").write_text(json.dumps(policy, indent=2), encoding="utf-8")
    (out_dir / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print("Wrote output/demo-run/{triage,handoff,policy,audit}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
