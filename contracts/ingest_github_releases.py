#!/usr/bin/env python3
"""Ingest latest GitHub release signals as A-class candidates.

Run:
  python contracts/ingest_github_releases.py --repos openai/openai-python,langchain-ai/langchain
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _now_trace(prefix: str, index: int) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"trace.{prefix}.{ts}.{index:03d}"


def fetch_latest_release(repo: str) -> dict | None:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "workato2026-ingest"})
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    except URLError:
        return None


def normalize_release(repo: str, release: dict, idx: int) -> dict:
    published = release.get("published_at") or datetime.now(timezone.utc).isoformat()
    body = (release.get("body") or "").strip().replace("\n", " ")
    summary = body[:240] if body else f"Latest release detected for {repo}."

    return {
        "candidate_id": f"cand-{repo.replace('/', '-')}-{release.get('id', idx)}",
        "project_id": "proj-demo",
        "source_class": "A",
        "source_type": "github",
        "evidence_grade": "A1",
        "candidate_url": release.get("html_url", f"https://github.com/{repo}/releases"),
        "published_at": published,
        "summary": summary,
        "claimed_change_type": ["feature"],
        "affected_stack": [repo.split("/")[-1]],
        "relevance_score": 0.72,
        "context_similarity": 0.7,
        "novelty_score": 0.6,
        "impact_score": 0.65,
        "trust_score": 0.9,
        "noise_risk_score": 0.25,
        "execution_cost_score": 0.3,
        "score_total": 72,
        "decision": "hint",
        "decision_reason": ["seed"],
        "trigger_reason": [f"latest release for {repo}"],
        "requires_user_confirm": False,
        "security_gate": "pass",
        "trace_id": _now_trace("ingest", idx),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repos",
        default="openai/openai-python,microsoft/autogen",
        help="comma-separated owner/repo list",
    )
    parser.add_argument(
        "--output",
        default="output/ingest/github_candidates.json",
        help="output json path",
    )
    args = parser.parse_args()

    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    candidates: list[dict] = []

    for idx, repo in enumerate(repos, start=1):
        release = fetch_latest_release(repo)
        if not release:
            continue
        candidates.append(normalize_release(repo, release, idx))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"wrote {len(candidates)} candidates to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
