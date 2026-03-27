import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import decision_engine  # noqa: E402


class TestDecisionEngine(unittest.TestCase):
    def _candidate(self):
        return {
            "candidate_id": "cand-001",
            "project_id": "proj-001",
            "source_class": "A",
            "source_type": "github",
            "evidence_grade": "A1",
            "candidate_url": "https://example.com/release",
            "published_at": "2026-03-27T09:00:00Z",
            "summary": "Official update for decision engine integration.",
            "claimed_change_type": ["feature"],
            "affected_stack": ["python", "workato"],
            "relevance_score": 0.82,
            "context_similarity": 0.8,
            "novelty_score": 0.5,
            "impact_score": 0.8,
            "trust_score": 0.9,
            "noise_risk_score": 0.2,
            "execution_cost_score": 0.3,
            "score_total": 84,
            "decision": "hint",
            "decision_reason": ["seed"],
            "trigger_reason": ["ingest"],
            "requires_user_confirm": False,
            "security_gate": "pass",
            "trace_id": "trace.day2.engine.0001",
        }

    def _snapshot(self):
        return {
            "project_id": "proj-001",
            "snapshot_time": "2026-03-27T10:00:00Z",
            "repo_urls": ["https://github.com/acme/proj"],
            "tech_stack": ["python"],
            "active_modules": ["decision-engine"],
            "current_goals": ["decision", "trace"],
            "open_problems": ["noise"],
            "non_goals": ["auto_commit"],
            "risk_tolerance": "medium",
            "latency_budget_ms": 1200,
            "cost_budget_daily_usd": 20,
            "security_constraints": ["readonly"],
            "acceptance_signals": ["official", "decision"],
            "rejection_signals": ["open_twitter_scrape", "auto_commit"],
            "trace_id": "trace.day2.snapshot.0001",
            "last_feedback": [],
        }

    def test_gate_order_is_fixed_for_full_path(self):
        candidate = self._candidate()
        result = decision_engine.decide_candidate(candidate, self._snapshot())
        self.assertEqual("deep_read", result["decision"])
        self.assertEqual(
            [
                "Evidence Gate",
                "Context Gate",
                "Profile Gate",
                "Policy Gate",
                "Action Gate",
            ],
            result["gate_path"],
        )

    def test_b_only_without_linked_a_is_mention(self):
        candidate = self._candidate()
        candidate["source_class"] = "B"
        candidate["source_type"] = "tweet_whitelist"
        candidate["evidence_grade"] = "A0"
        result = decision_engine.decide_candidate(candidate)
        self.assertEqual("mention", result["decision"])
        self.assertIn("B_WITHOUT_A_EVIDENCE", result["decision_reason"])

    def test_security_block_is_discard(self):
        candidate = self._candidate()
        candidate["security_gate"] = "block"
        result = decision_engine.decide_candidate(candidate)
        self.assertEqual("discard", result["decision"])
        self.assertIn("POLICY_BLOCK", result["decision_reason"])

    def test_action_stage_requires_user_confirm(self):
        candidate = self._candidate()
        result = decision_engine.decide_candidate(
            candidate,
            requested_stage="action",
            deep_read_completed=True,
            user_confirmed=False,
        )
        self.assertNotEqual("action", result["decision"])
        self.assertIn("ACTION_NEEDS_CONFIRM", result["decision_reason"])

    def test_action_stage_after_confirm(self):
        candidate = self._candidate()
        result = decision_engine.decide_candidate(
            candidate,
            requested_stage="action",
            deep_read_completed=True,
            user_confirmed=True,
        )
        self.assertEqual("action", result["decision"])
        self.assertIn("ACTION_CONFIRMED", result["decision_reason"])

    def test_high_noise_degrades_level(self):
        candidate = self._candidate()
        candidate["noise_risk_score"] = 0.92
        result = decision_engine.decide_candidate(candidate)
        self.assertEqual("hint", result["decision"])
        self.assertIn("HIGH_NOISE_RISK", result["decision_reason"])

    def test_profile_rejection_degrades_level(self):
        candidate = self._candidate()
        candidate["summary"] = "this proposes auto_commit to repository"
        result = decision_engine.decide_candidate(candidate, self._snapshot())
        self.assertEqual("hint", result["decision"])
        self.assertIn("PROFILE_MISMATCH", result["decision_reason"])

    def test_profile_match_can_boost_level(self):
        candidate = self._candidate()
        candidate["relevance_score"] = 0.72
        result = decision_engine.decide_candidate(candidate, self._snapshot())
        self.assertEqual("deep_read", result["decision"])
        self.assertIn("PROFILE_MATCH_BOOST", result["decision_reason"])

    def test_strict_validation_can_reject_payload(self):
        candidate = self._candidate()
        candidate.pop("trace_id")
        result = decision_engine.decide_candidate(candidate, strict_validation=True)
        self.assertEqual("discard", result["decision"])
        self.assertIn("INVALID_CANDIDATE_PAYLOAD", result["decision_reason"])
        self.assertGreater(len(result["validation_errors"]), 0)

    def test_handoff_payload_shape(self):
        candidate = self._candidate()
        result = decision_engine.decide_candidate(candidate)
        handoff = decision_engine.build_handoff_payload(candidate, result)
        self.assertEqual(candidate["candidate_id"], handoff["candidate_id"])
        self.assertEqual(result["decision"], handoff["decision"])
        self.assertIn("trace_id", handoff)

    def test_audit_event_shape(self):
        candidate = self._candidate()
        result = decision_engine.decide_candidate(candidate)
        event = decision_engine.build_audit_event(
            result,
            who="system",
            source="decision_engine",
            files_accessed=["/workspace/project/src/module.py"],
            user_confirmed=False,
        )
        self.assertEqual("system", event["who"])
        self.assertEqual(result["trace_id"], event["trace_id"])
        self.assertIn("when", event)
        self.assertIn("action_taken", event)

    def test_persist_handoff_payload(self):
        candidate = self._candidate()
        result = decision_engine.decide_candidate(candidate)
        handoff = decision_engine.build_handoff_payload(candidate, result)

        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp) / "handoff.jsonl"
            info = decision_engine.persist_handoff_payload(handoff, str(outbox))
            self.assertEqual(str(outbox), info["outbox_path"])
            lines = outbox.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(1, len(lines))
            saved = json.loads(lines[0])
            self.assertEqual(handoff["trace_id"], saved["trace_id"])

    def test_persist_handoff_payload_rejects_bad_payload(self):
        candidate = self._candidate()
        result = decision_engine.decide_candidate(candidate)
        handoff = decision_engine.build_handoff_payload(candidate, result)
        handoff.pop("trace_id")

        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp) / "handoff.jsonl"
            with self.assertRaises(ValueError):
                decision_engine.persist_handoff_payload(handoff, str(outbox))

    def test_persist_audit_event(self):
        candidate = self._candidate()
        result = decision_engine.decide_candidate(candidate)
        event = decision_engine.build_audit_event(result, who="system", source="decision_engine")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            info = decision_engine.persist_audit_event(event, str(path))
            self.assertEqual(str(path), info["audit_path"])
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(1, len(lines))
            saved = json.loads(lines[0])
            self.assertEqual(event["trace_id"], saved["trace_id"])


if __name__ == "__main__":
    unittest.main()
