# Security Contract - Local Execution Boundary (MVP)

## Goal
Define enforceable default behavior for local execution via MCP + local skills. This is a control contract, not a principle document.

## 1) Default Permission State
System defaults:
- Read-only mode by default.
- Read only latest `project_snapshot` by default.
- Do not scan full repository by default.
- Do not write files by default.
- Do not use production credentials for high-risk actions by default.

## 2) Deep Read Permission Conditions
Local `repo_compare` is allowed only when all conditions pass:
- Candidate passed `Evidence Gate`.
- Candidate passed `Context Gate`.
- User approved, or user pre-authorized read-only compare.
- Access is restricted to `allowed_dirs`.
- `max_files <= 5`.
- `max_depth <= 2`.

If any condition fails, deep read is blocked with auditable reason.

## 3) Write Permission (MVP)
Allowed low-risk write actions only:
- Write watchlist entries.
- Write note/follow-up records.

Explicitly prohibited in MVP:
- Auto-modifying local code.
- Auto-creating git commits.
- Auto-sending external messages.
- Auto-creating high-impact tasks.
- Auto-calling production-impact third-party APIs.

## 4) Credential Rules
- GitHub access uses user-owned OAuth/token.
- Local skill receives least privilege per task.
- Workato and MCP must not share a universal service account.
- Every action must be attributable to a user identity or system identity.

## 5) Audit Trail Requirements
Each key action must log:
- `who`
- `when`
- `source`
- `trigger_reason`
- `files_accessed`
- `action_taken`
- `user_confirmed`
- `trace_id`

## 6) Policy Gate Outcomes
- `pass`: continue to Action Gate.
- `review`: require user confirmation before execution.
- `block`: terminate candidate processing.

## 7) Runtime Guardrail Checklist
Before executing any local tool call:
- Validate `trace_id` exists.
- Validate requested action is within allowed action set.
- Validate access path is in `allowed_dirs`.
- Validate file/depth limits.
- Validate identity and auth context.
- Validate policy outcome (`pass` or confirmed `review`).

If any check fails, deny and log.

## 8) Acceptance Tests
- Test A: request full repo scan without allowlist -> denied.
- Test B: request write code file in MVP -> denied.
- Test C: request watchlist write with confirmed review -> allowed.
- Test D: missing `trace_id` -> denied and logged.
