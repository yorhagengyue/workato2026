# Decision Table - Attention Decision System

## Scope
This table is the implementation contract for candidate triage. Runtime services must follow this exact gate order and action policy.

## Source Classes
- `A` (first-party facts): GitHub Trending, pinned repos, repo updates, official AI release notes/docs/blog/changelog.
- `B` (interpretation-only): whitelist author tweets.

Hard rule:
- `B` cannot trigger `deep_read` alone.
- `B` can only trigger `mention` or raise priority of an existing `A` candidate.

## Mandatory Gate Order
No skipping or reordering is allowed.

1. `Evidence Gate`
2. `Context Gate`
3. `Profile Gate`
4. `Policy Gate`
5. `Action Gate`

## Decision Logic

| Step | Condition | Result | Required reason key |
|---|---|---|---|
| Evidence Gate | `source_class=B` and no linked `A` evidence | `decision=mention` (max) | `B_WITHOUT_A_EVIDENCE` |
| Evidence Gate | `source_class=A` or (`A+B` linked) | Continue | `EVIDENCE_PASS` |
| Context Gate | `relevance_score < 0.45` | `decision=discard` | `LOW_CONTEXT_RELEVANCE` |
| Context Gate | `0.45 <= relevance_score <= 0.75` | Candidate for `hint` only | `MID_CONTEXT_RELEVANCE` |
| Context Gate | `relevance_score > 0.75` and `evidence_grade >= A1` | Candidate for `deep_read` | `HIGH_CONTEXT_RELEVANCE` |
| Profile Gate | Conflicts with `rejection_signals` or non-goals | Degrade one level | `PROFILE_MISMATCH` |
| Profile Gate | Matches `acceptance_signals` or active goals | Keep level | `PROFILE_MATCH` |
| Policy Gate | `security_gate=block` | `decision=discard` | `POLICY_BLOCK` |
| Policy Gate | `noise_risk_score=high` | Degrade one level | `HIGH_NOISE_RISK` |
| Action Gate | `deep_read` candidate + (A + high relevance + policy pass) | `decision=deep_read` | `DEEP_READ_RULE_A` |
| Action Gate | `deep_read` candidate + (A + explicit user interest) | `decision=deep_read` | `DEEP_READ_RULE_B` |
| Action Gate | Post deep read and user confirms | `decision=action` | `ACTION_CONFIRMED` |

## Action Policy
- `discard`: low relevance, policy blocked, or B-only low value.
- `mention`: B-only signal or low-confidence hint.
- `hint`: relevant A or A+B signal, but not deep-read worthy.
- `deep_read`: only if one deep-read rule is met.
- `action`: only after deep-read output and user confirmation.

## Threshold Contract (MVP)
- `relevance_score < 0.45`: `discard`
- `0.45-0.75`: `hint`
- `> 0.75` and `evidence_grade >= A1`: deep-read candidate
- `B` only: max `mention`
- `noise_risk_score=high`: degrade by one level
- `security_gate=block`: hard stop

## Required Decision Output Fields
Every processed candidate must include:
- `decision`
- `decision_reason[]`
- `evidence_grade`
- `relevance_score`
- `noise_risk_score`
- `requires_user_confirm`
- `trace_id`

## Testable Acceptance Cases
- Case 1: B-only hot tweet -> result is `mention`, never `deep_read`.
- Case 2: A-source and `relevance_score=0.80` with policy pass -> `deep_read` allowed.
- Case 3: A-source with `security_gate=block` -> hard `discard`.
- Case 4: Deep-read completed but no user confirmation -> no `action`.
