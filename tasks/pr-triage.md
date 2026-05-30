# PR Triage — 2026-05-30 (salvage pass)

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · DEFER · CLOSE-SUPERSEDED · ESCALATE · CLOSE-NO-OP

## Morning review (Phase 1) — reference

Inventory and dispositions for the `0 13` review-and-merge run are in the review branch artifacts (merged into this file’s companion `tasks/pr-review-2026-05-30.md`).

## Salvage pass (Phase 2, cron `0 17`)

### Reconciliation

| PR | Repo | Phase 1 disposition | Live state at salvage | Action |
| --- | ---: | --- | --- | --- |
| #957 | email-security-pipeline | DEFER | MERGED | Dropped from queue |
| #956 | email-security-pipeline | DEFER | MERGED | Dropped from queue |
| #962 | email-security-pipeline | DEFER | OPEN, bandit fail | **CLOSE-NO-OP** — unpins SHAs to tags |
| #1093 | personal-config | ESCALATE | OPEN, CI green | **ESCALATE** (no change) |
| #1095 | personal-config | (draft docs) | OPEN draft | **CLOSE-SUPERSEDED** by salvage artifact PR |

### Conflict scan

No open PRs with `DIRTY`, `BEHIND`, or `CONFLICTING` merge state across any configured repo.

### Dispositions (salvage only)

| Disposition | Count | PRs |
| --- | ---: | --- |
| CLOSE-NO-OP | 1 | email-security-pipeline #962 |
| ESCALATE (carry) | 1 | personal-config #1093 |

### Security / trust notes

| PR | Tier | Assessment |
| --- | --- | --- |
| #1093 | T2 trust-boundary | Micro-opts on PR automation scratch helpers; green CI does not waive human merge (Lesson 0z). |
| #962 | CI/INFRA | Automation moved pins **from** full SHAs **to** version tags — violates org policy; closed without salvage branch. |

## Human merge queue

| PR | Repo | Why human |
| --- | --- | --- |
| #1093 | personal-config | Trust-boundary on `run_merges.py` / `scratch_*` |
