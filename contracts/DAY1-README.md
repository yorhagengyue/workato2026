# Day 1 Artifacts

## 1) Schema Validator
- Script: `contracts/validator.py`
- Schemas:
  - `contracts/schemas/project_snapshot.schema.json`
  - `contracts/schemas/repo_compare.schema.json`

Run:
```bash
python contracts/validator.py project_snapshot contracts/test-cases/project_snapshot.valid.json
python contracts/validator.py repo_compare contracts/test-cases/repo_compare.valid.json
```

Expected:
- Valid samples return `VALID`.
- Invalid samples return `INVALID` with contract violations.

## 2) Decision Test Matrix
- `contracts/decision-test-matrix.md`

Covers:
- B-only cannot deep_read.
- `security_gate=block` must discard.
- No user confirm cannot action.
- Security negative scenarios must deny and log.

## 3) Policy Gate + Automated Tests (Day 2 bootstrap)
- Runtime gate: `contracts/policy_gate.py`
- Automated tests: `contracts/tests/test_contracts.py`

Run:
```bash
python -m unittest discover -s contracts/tests -v
```

Coverage includes:
- `source_type <-> source_class` consistency checks.
- URL/URI validity checks for `candidate_url` and `repo_urls`.
- Security negative cases (`ST-*`) enforced as deny-and-log tests.

## Included Test Vectors
- `contracts/test-cases/repo_compare.invalid.b_only_deep_read.json`
- `contracts/test-cases/repo_compare.invalid.policy_block_not_discard.json`
- `contracts/test-cases/repo_compare.invalid.action_without_confirm.json`
- `contracts/test-cases/repo_compare.invalid.missing_trace_id.json`
- `contracts/test-cases/security-negative-cases.json`
