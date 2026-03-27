#!/usr/bin/env python3
"""Ingest official AI vendor updates from docs/blog/changelog URLs.

Run:
  python contracts/ingest_official_updates.py
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import scoring


def _now_trace(prefix: str, index: int) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"trace.{prefix}.{ts}.{index:03d}"


def _load_snapshot(path: str) -> dict | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None


def _fetch(url: str) -> tuple[str, dict[str, str]] | None:
    req = Request(url, headers={"User-Agent": "workato2026-official-ingest"})
    try:
        with urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return body, headers
    except URLError:
        return None


def _strip_tags(html: str) -> str:
    text = re.sub(r"<script[\\s\\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\\s\\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\\s+", " ", text)
    return unescape(text).strip()


def _extract_from_xml(content: str) -> tuple[str, str] | None:
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return None

    channel = root.find("channel")
    if channel is not None:
        item = channel.find("item")
        if item is not None:
            title = (item.findtext("title") or "").strip()
            desc = (item.findtext("description") or "").strip()
            if title:
                return title, _strip_tags(desc)[:240]

    entries = root.findall("{http://www.w3.org/2005/Atom}entry")
    if entries:
        entry = entries[0]
        title = (entry.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
        summary = (entry.findtext("{http://www.w3.org/2005/Atom}summary") or "").strip()
        if title:
            return title, _strip_tags(summary)[:240]

    return None


def _extract_from_html(content: str) -> tuple[str, str]:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", content, flags=re.IGNORECASE | re.DOTALL)
    title = _strip_tags(title_match.group(1)) if title_match else "Official update"

    meta_desc = ""
    meta_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if meta_match:
        meta_desc = _strip_tags(meta_match.group(1))

    snippet = _strip_tags(content)[:240]
    summary = meta_desc[:240] if meta_desc else snippet
    return title, summary


def normalize_official(url: str, title: str, summary: str, idx: int, published_at: str) -> dict:
    source_type = "official_blog" if any(k in url for k in ["blog", "news"]) else "official_doc"
    change_types = ["feature"]
    lowered = f"{title} {summary}".lower()
    if "security" in lowered:
        change_types.append("security")
    if "breaking" in lowered or "deprecat" in lowered:
        change_types.append("breaking")

    return {
        "candidate_id": f"cand-official-{idx:03d}",
        "project_id": "proj-demo",
        "source_class": "A",
        "source_type": source_type,
        "evidence_grade": "A1",
        "candidate_url": url,
        "published_at": published_at,
        "summary": f"{title}: {summary}"[:240],
        "claimed_change_type": sorted(set(change_types)),
        "affected_stack": ["llm-platform"],
        "relevance_score": 0.0,
        "context_similarity": 0.0,
        "novelty_score": 0.0,
        "impact_score": 0.0,
        "trust_score": 0.0,
        "noise_risk_score": 0.0,
        "execution_cost_score": 0.0,
        "score_total": 0.0,
        "decision": "hint",
        "decision_reason": ["seed"],
        "trigger_reason": [f"official update source {url}"],
        "requires_user_confirm": False,
        "security_gate": "pass",
        "trace_id": _now_trace("official", idx),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources",
        default="https://platform.openai.com/docs/changelog,https://docs.anthropic.com/en/release-notes/api,https://ai.google.dev/gemini-api/docs/changelog",
        help="comma-separated official docs/blog/changelog URLs",
    )
    parser.add_argument(
        "--snapshot",
        default="",
        help="optional project_snapshot json for context-aware scoring",
    )
    parser.add_argument(
        "--output",
        default="output/ingest/official_candidates.json",
        help="output json path",
    )
    args = parser.parse_args()

    snapshot = _load_snapshot(args.snapshot)
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]

    candidates: list[dict] = []
    for idx, url in enumerate(sources, start=1):
        fetched = _fetch(url)
        if not fetched:
            continue

        content, headers = fetched
        published_at = headers.get("last-modified", "")
        if published_at:
            try:
                dt = datetime.strptime(published_at, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                published_iso = dt.isoformat()
            except ValueError:
                published_iso = datetime.now(timezone.utc).isoformat()
        else:
            published_iso = datetime.now(timezone.utc).isoformat()

        extracted = _extract_from_xml(content)
        if extracted:
            title, summary = extracted
        else:
            title, summary = _extract_from_html(content)

        raw = normalize_official(url, title, summary, idx, published_iso)
        candidates.append(scoring.score_candidate(raw, snapshot))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(candidates)} candidates to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
