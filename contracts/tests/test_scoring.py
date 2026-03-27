import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scoring  # noqa: E402


class TestScoring(unittest.TestCase):
    def _candidate(self, summary: str):
        return {
            "source_class": "A",
            "source_type": "official_doc",
            "evidence_grade": "A1",
            "summary": summary,
            "claimed_change_type": ["feature"],
            "affected_stack": ["python", "mcp"],
            "published_at": "2026-03-27T09:00:00Z",
        }

    def _snapshot(self):
        return {
            "tech_stack": ["python", "workato", "mcp"],
            "current_goals": ["safe_actions", "decision"],
        }

    def test_scores_are_in_valid_ranges(self):
        scored = scoring.score_candidate(self._candidate("Official update for mcp auth"), self._snapshot())
        for key in [
            "relevance_score",
            "context_similarity",
            "novelty_score",
            "impact_score",
            "trust_score",
            "noise_risk_score",
            "execution_cost_score",
        ]:
            self.assertGreaterEqual(scored[key], 0.0)
            self.assertLessEqual(scored[key], 1.0)
        self.assertGreaterEqual(scored["score_total"], 0.0)
        self.assertLessEqual(scored["score_total"], 100.0)

    def test_security_keywords_increase_impact(self):
        baseline = scoring.score_candidate(self._candidate("Official update"), self._snapshot())
        security = self._candidate("Security migration required for auth compatibility")
        security["claimed_change_type"] = ["feature", "security", "breaking"]
        boosted = scoring.score_candidate(security, self._snapshot())
        self.assertGreater(boosted["impact_score"], baseline["impact_score"])
        self.assertGreater(boosted["score_total"], baseline["score_total"])

    def test_snapshot_overlap_affects_context_similarity(self):
        matched = scoring.score_candidate(self._candidate("python mcp release"), self._snapshot())
        off_topic = scoring.score_candidate(self._candidate("android kotlin ui update"), self._snapshot())
        self.assertGreater(matched["context_similarity"], off_topic["context_similarity"])


if __name__ == "__main__":
    unittest.main()
