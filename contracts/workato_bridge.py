#!/usr/bin/env python3
"""Bridge local outbox/audit records to Workato webhook recipes.

This is the integration step from local JSONL persistence to Workato Data Tables
(via webhook-triggered recipes).

Env defaults:
- WORKATO_HANDOFF_WEBHOOK_URL
- WORKATO_AUDIT_WEBHOOK_URL
- WORKATO_WEBHOOK_BEARER_TOKEN (optional)

Run dry-run:
  python contracts/workato_bridge.py

Send mode:
  python contracts/workato_bridge.py --send
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def post_json(url: str, payload: dict, bearer_token: str = "") -> int:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Trace-Id": str(payload.get("trace_id", "")),
    }
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    req = Request(url, data=data, headers=headers, method="POST")
    with urlopen(req, timeout=30) as resp:
        return int(resp.status)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff-jsonl", default="output/workato-outbox/handoff.jsonl")
    parser.add_argument("--audit-jsonl", default="output/audit/tbl_audit_events.jsonl")
    parser.add_argument("--handoff-url", default=os.getenv("WORKATO_HANDOFF_WEBHOOK_URL", ""))
    parser.add_argument("--audit-url", default=os.getenv("WORKATO_AUDIT_WEBHOOK_URL", ""))
    parser.add_argument("--send", action="store_true", help="actually POST to Workato webhooks")
    args = parser.parse_args()

    handoff_rows = read_jsonl(Path(args.handoff_jsonl))
    audit_rows = read_jsonl(Path(args.audit_jsonl))

    print(f"handoff_rows={len(handoff_rows)} from {args.handoff_jsonl}")
    print(f"audit_rows={len(audit_rows)} from {args.audit_jsonl}")

    if not args.send:
        print("dry-run mode: no network POST")
        return 0

    if not args.handoff_url or not args.audit_url:
        print("missing webhook URL(s): set --handoff-url/--audit-url or env vars")
        return 2

    token = os.getenv("WORKATO_WEBHOOK_BEARER_TOKEN", "")

    handoff_ok = 0
    for row in handoff_rows:
        status = post_json(args.handoff_url, row, token)
        if 200 <= status < 300:
            handoff_ok += 1

    audit_ok = 0
    for row in audit_rows:
        status = post_json(args.audit_url, row, token)
        if 200 <= status < 300:
            audit_ok += 1

    print(f"sent_handoff_ok={handoff_ok}/{len(handoff_rows)}")
    print(f"sent_audit_ok={audit_ok}/{len(audit_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
