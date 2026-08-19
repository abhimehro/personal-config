# Stage Run Record — YYYY-MM-DD

## Identity

- Stage: `stage1 | stage2 | stage3`
- Trigger: `cron | on-demand | recovery`
- Configuration version and policy revision:
- Start and end UTC:
- Ledger revision read and resulting revision:
- Dashboard export fingerprint and memory mode:
- Calibration mode: `report_only | approved_completion | revoked`

## Inputs and reconciliation

- Items considered:
- Items skipped as unchanged:
- Items invalidated by SHA drift:
- Items resolved outside the workflow:

## Mandatory per-item evidence, action, and outcome record

One row is required for every processed, proposed, skipped, retried, or completed item. A missing field is `ANALYSIS_ERROR`, not an invitation to fill it from memory.

| Ledger key | Repository / PR | Observed vs ledger base/head SHA | Owner before → after | GitHub identity / author type | Classification / risk / sticky paths | Guardrail outcome | Changed paths | Evidence URLs | Proposed route / actual action | Mode / audit ID / action count | Retry or error | Final observed outcome / calibration correctness | Provenance or canonical relation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Revision-checked handoffs and human decisions

| Ledger key | Event ID / idempotency key | Expected → resulting revision | Next owner | One next action | Safe default | Expiry | Receiver acknowledgement |
|---|---|---|---|---|---|---|---|

## Continuity

- Successful pattern reused:
- Failed approach not to repeat:
- New lesson candidate and the future rule it changes:
- Configuration or policy gap:
- Historical-import sources or fingerprints processed:

## Metrics

- Inventory / recovery / reconciliation count:
- Merged:
- Closed:
- Drafts created:
- Decision packets created:
- Analysis errors:
- State-changing actions, including failed attempts and retries:
