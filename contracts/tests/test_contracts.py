import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import policy_gate  # noqa: E402
import validator  # noqa: E402


class TestValidatorContracts(unittest.TestCase):
    def _load(self, relative_path: str):
        p = ROOT / relative_path
        return json.loads(p.read_text(encoding="utf-8-sig"))

    def test_project_snapshot_valid(self):
        payload = self._load("test-cases/project_snapshot.valid.json")
        self.assertEqual([], validator.validate_project_snapshot(payload))

    def test_repo_compare_valid(self):
        payload = self._load("test-cases/repo_compare.valid.json")
        self.assertEqual([], validator.validate_repo_compare(payload))

    def test_b_only_cannot_deep_read(self):
        payload = self._load("test-cases/repo_compare.invalid.b_only_deep_read.json")
        errors = validator.validate_repo_compare(payload)
        self.assertTrue(any("B-only candidate cannot deep_read/action" in e for e in errors))

    def test_security_gate_block_must_discard(self):
        payload = self._load("test-cases/repo_compare.invalid.policy_block_not_discard.json")
        errors = validator.validate_repo_compare(payload)
        self.assertTrue(any("security_gate=block must produce decision=discard" in e for e in errors))

    def test_action_must_require_user_confirm(self):
        payload = self._load("test-cases/repo_compare.invalid.action_without_confirm.json")
        errors = validator.validate_repo_compare(payload)
        self.assertTrue(any("action requires user confirmation" in e for e in errors))

    def test_missing_trace_id_denied(self):
        payload = self._load("test-cases/repo_compare.invalid.missing_trace_id.json")
        errors = validator.validate_repo_compare(payload)
        self.assertTrue(any("missing_required=['trace_id']" in e for e in errors))

    def test_source_type_class_consistency_enforced(self):
        payload = self._load("test-cases/repo_compare.valid.json")
        payload["source_type"] = "tweet_whitelist"
        payload["source_class"] = "A"
        errors = validator.validate_repo_compare(payload)
        self.assertTrue(any("source_type=tweet_whitelist requires source_class=B" in e for e in errors))

    def test_candidate_url_must_be_http_or_https(self):
        payload = self._load("test-cases/repo_compare.valid.json")
        payload["candidate_url"] = "not-a-url"
        errors = validator.validate_repo_compare(payload)
        self.assertTrue(any("candidate_url must be valid http/https URL" in e for e in errors))

    def test_repo_urls_must_be_http_or_https(self):
        payload = self._load("test-cases/project_snapshot.valid.json")
        payload["repo_urls"] = ["file:///tmp/repo"]
        errors = validator.validate_project_snapshot(payload)
        self.assertTrue(any("repo_urls must contain valid http/https URLs" in e for e in errors))


class TestPolicyGateNegativeCases(unittest.TestCase):
    def _load_cases(self):
        p = ROOT / "test-cases/security-negative-cases.json"
        return json.loads(p.read_text(encoding="utf-8-sig"))

    def test_security_negative_cases_deny_and_log(self):
        for case in self._load_cases():
            result = policy_gate.evaluate_runtime_request(case["request"])
            self.assertEqual("DENY", result["decision"], msg=case["id"])
            self.assertGreater(len(result["reasons"]), 0, msg=case["id"])
            self.assertEqual("DENY", result["log"]["decision"], msg=case["id"])

    def test_policy_gate_allows_bounded_read_only_deep_read(self):
        request = {
            "trace_id": "trace.day2.security.allow01",
            "allowed_dirs": ["/workspace/project/src"],
            "requested_path": "/workspace/project/src/module",
            "max_files": 3,
            "max_depth": 2,
            "action_type": "deep_read",
            "security_gate": "pass",
        }
        result = policy_gate.evaluate_runtime_request(request)
        self.assertEqual("ALLOW", result["decision"])
        self.assertEqual([], result["reasons"])


if __name__ == "__main__":
    unittest.main()
