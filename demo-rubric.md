# Demo Rubric - NAISC Workato Track Two

## Purpose
Provide a fixed demonstration rubric that maps directly to judging expectations: innovation, technical usage, value, trust/safety, and UX clarity.

## Required Demo Scenes (Must all appear)

### Scene 1: Low-Noise Filtering
Show multiple incoming candidates where most are filtered out and only one becomes a lightweight hint.
Evidence to show:
- Input candidate count.
- Filtered count.
- Final interruption count.

### Scene 2: "Talk First, Analyze Later"
Show the assistant sending a short conversational prompt first, not jumping directly to a long deep-read report.
Evidence to show:
- First response is a concise hint/question.
- No deep read triggered before user intent.

### Scene 3: Controlled Deep Read
Show user confirmation before MCP triggers local skill execution.
On-screen controls must show:
- Read-only mode.
- `allowed_dirs` restriction.
- `max_files` limit.
- `trace_id`.

### Scene 4: Controlled Action
After deep read, show exactly one low-risk action (recommended: add watchlist entry).
Evidence to show:
- User confirmation captured.
- Action type is MVP-allowed.
- Audit record generated.

### Scene 5: Failure Fallback
Show a candidate that would normally deep-read but is blocked by `Policy Gate`.
Evidence to show:
- Block reason.
- No local execution occurred.
- Audit log includes blocked decision.

## Quantitative Comparison Table (Mandatory)
Use a consistent 4-metric before/after table:
- Total candidates
- Actual interruptions
- Deep-read count
- Adopted actions

Example scriptable baseline:
- Before: user reviews 20, interrupts 20, deep reads 0 (manual), adopted actions unknown.
- After: system receives 20, interrupts 3, deep reads 1, adopted actions 1.

## Evidence Capture Checklist
- Decision trace for each shown candidate.
- Gate-by-gate decision reasons.
- Security policy result (`pass/review/block`).
- User confirmation event for deep read and action.
- Audit log snippet with `trace_id`.

## Pass/Fail Criteria
Pass only if:
- All 5 scenes are shown.
- B-only signal never triggers deep read.
- At least one policy block is demonstrated.
- Before/after metrics table is shown with consistent definitions.

Fail if any of the above is missing.
