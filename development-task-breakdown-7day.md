# Development Task Breakdown + Ownership + 7-Day Sprint

## Scope Lock
This sprint implements only MVP-required modules:
- Evidence Gate
- Policy Gate
- Audit Trail
- Feedback Loop Lite

Out of scope this sprint:
- Complex learning systems
- Multi-platform source expansion
- Auto code modification
- Open tweet crawling
- High-risk external actions

## Team Roles
- `Lead Engineer`: decision engine + schema + contracts
- `Integration Engineer`: Workato flows + MCP bridge
- `Local Agent Engineer`: local skill runtime guards + limits
- `Frontend Engineer`: operator UI + decision trace panel
- `QA/PM`: acceptance tests + demo script + evidence pack

## Work Packages

### WP1 - Contracted Schemas (P0)
Owner: Lead Engineer
Tasks:
- Freeze `project_snapshot` fields (include acceptance/rejection signals, budgets, feedback, trace).
- Freeze `repo_compare` fields (include evidence/noise/cost/trigger/security/trace).
- Add schema validators and default values.
Acceptance:
- Invalid candidate payload is rejected with reason.
- All required decision output fields are guaranteed.

### WP2 - Decision Engine (P0)
Owner: Lead Engineer
Tasks:
- Implement fixed 5-gate order.
- Implement hard rules for B-only handling.
- Implement threshold mapping for discard/hint/deep_read/action candidate.
- Implement downgrade logic for high noise risk.
Acceptance:
- Deterministic output for same input.
- Gate order cannot be bypassed.
- B-only never returns `deep_read`.

### WP3 - Policy Gate + Runtime Guardrails (P0)
Owner: Local Agent Engineer
Tasks:
- Enforce read-only by default.
- Enforce `allowed_dirs`, `max_files<=5`, `max_depth<=2`.
- Block all prohibited MVP actions.
- Enforce user confirmation checks for review/action.
Acceptance:
- Disallowed file access and prohibited writes are denied and logged.
- Missing `trace_id` request is denied.

### WP4 - Workato + MCP Responsibility Split (P1)
Owner: Integration Engineer
Tasks:
- Keep Workato orchestration-only; no strategy scoring in flows.
- Keep MCP bridge-only; no policy decisions in tools.
- Define stable handoff payload between central decision layer and local runtime.
Acceptance:
- One decision source of truth.
- Same candidate yields same action across invocation paths.

### WP5 - Audit Trail (P1)
Owner: Local Agent Engineer
Tasks:
- Implement audit events for key actions.
- Persist required fields (`who/when/source/trigger_reason/files_accessed/action_taken/user_confirmed/trace_id`).
- Expose trace view for demo.
Acceptance:
- Every deep_read/action/block has a corresponding auditable event.

### WP6 - Feedback Loop Lite (P2)
Owner: Lead Engineer
Tasks:
- Record user feedback (`upvote/downvote/mute/act`).
- Apply bounded weight adjustments only (no ML model).
Acceptance:
- Feedback changes ranking weight within capped range.
- Decision reasons include adjusted factors.

### WP7 - Demo UI + Evidence Pack (P1)
Owner: Frontend Engineer + QA/PM
Tasks:
- Build panel showing gate-by-gate decision path.
- Add scenes required by `demo-rubric.md`.
- Build before/after metric table component.
Acceptance:
- All 5 required scenes are runnable.
- Metric definitions are consistent in deck and demo.

## 7-Day Sprint Plan

### Day 1
- Finalize schema contracts and validators (WP1).
- Finalize decision test matrix from decision table.

### Day 2
- Implement Evidence/Context/Profile/Action gates (WP2).
- Add unit tests for thresholds and B-only constraints.

### Day 3
- Implement Policy Gate runtime checks (WP3).
- Add negative tests for blocked operations.

### Day 4
- Implement Workato/MCP handoff payload and boundaries (WP4).
- Integrate audit event emission (WP5).

### Day 5
- Implement Feedback Loop Lite and reason surfacing (WP6).
- Wire trace panel in UI (WP7 partial).

### Day 6
- Build and rehearse 5 demo scenes end-to-end (WP7).
- Produce before/after quantitative table.

### Day 7
- Full dry-run with failure fallback scenario.
- Fix blockers, freeze script, freeze evidence bundle.

## Definition of Done (Sprint)
- Decision behavior matches `decision-table.md`.
- Runtime behavior matches `security-contract.md`.
- Demo matches `demo-rubric.md` with all evidence artifacts.
- No prohibited MVP action can execute.
- Core test suite green (unit + integration + demo checks).
