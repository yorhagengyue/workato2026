# Decision Test Matrix (Day 1)

## Purpose
Convert `decision-table.md` and `security-contract.md` into explicit, testable cases that block free interpretation during implementation.

## Global Invariants
- Gate order is fixed: `Evidence -> Context -> Profile -> Policy -> Action`.
- `B` source cannot produce `deep_read` or `action`.
- `security_gate=block` must terminate to `discard`.
- `action` requires explicit user confirmation.
- Missing `trace_id` must be denied and logged.

## Decision Acceptance Cases

| ID | Input Summary | Expected Decision | Must Include Reason |
|---|---|---|---|
| DT-001 | `source_class=B`, no linked A, high relevance | `mention` (or `discard`) | `B_WITHOUT_A_EVIDENCE` |
| DT-002 | A-source, `relevance_score=0.82`, `security_gate=pass` | `deep_read` allowed | `EVIDENCE_PASS`, `HIGH_CONTEXT_RELEVANCE` |
| DT-003 | A-source, `relevance_score=0.30` | `discard` | `LOW_CONTEXT_RELEVANCE` |
| DT-004 | A-source, `relevance_score=0.60` | `hint` | `MID_CONTEXT_RELEVANCE` |
| DT-005 | Candidate with `security_gate=block` | `discard` | `POLICY_BLOCK` |
| DT-006 | Candidate wants `action` with `requires_user_confirm=false` | deny / not `action` | `ACTION_NEEDS_CONFIRM` |
| DT-007 | `evidence_grade=A0` attempting `deep_read` | deny deep_read | `DEEP_READ_NEEDS_A_EVIDENCE` |
| DT-008 | `noise_risk_score>=0.8` at action level | degrade one level | `HIGH_NOISE_RISK` |

## Security Negative Cases

| ID | Input Summary | Expected Outcome | Audit Requirement |
|---|---|---|---|
| ST-001 | Missing `trace_id` in request | `DENY` | log contains deny reason and request fingerprint |
| ST-002 | Path outside `allowed_dirs` | `DENY` | log includes blocked path |
| ST-003 | `max_files > 5` or `max_depth > 2` | `DENY` | log includes limit violation |
| ST-004 | Request to write code file in MVP | `DENY` | log includes prohibited action type |
| ST-005 | Request full repository scan | `DENY` | log includes scope violation |
| ST-006 | `security_gate=block` but execution still requested | `DENY` | log includes policy-block enforcement |

## Sample Test Vectors in Repo
- `contracts/test-cases/project_snapshot.valid.json`
- `contracts/test-cases/repo_compare.valid.json`
- `contracts/test-cases/repo_compare.invalid.b_only_deep_read.json`
- `contracts/test-cases/repo_compare.invalid.policy_block_not_discard.json`
- `contracts/test-cases/repo_compare.invalid.action_without_confirm.json`
- `contracts/test-cases/repo_compare.invalid.missing_trace_id.json`

## Mapping to Automation (Next Step)
- Convert `DT-*` into decision-engine unit tests.
- Convert `ST-*` into policy-gate integration tests.
- Enforce CI rule: any invariant break blocks merge.
