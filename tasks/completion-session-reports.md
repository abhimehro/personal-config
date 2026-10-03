# Completion Session Reports

> Append-only log for the Automated PR Completion Agent. The Completion Agent is
> the only writer. It reads review and salvage reports but must not modify them.
> Before appending, it validates the ledger and updates its owned entries only
> through revision-checked events.

## Run record template

See [`tasks/pr-stage-run-record.example.md`](pr-stage-run-record.example.md).
Each run must identify the ledger revision read and resulting revision,
dashboard fingerprint, calibration mode, items reconciled, observed versus
ledger anchors, owner transition, GitHub identity, classification/risk/sticky
paths, evidence URLs, proposed and final outcomes, audit IDs, action count,
Stage 2 work items, decision packets, retries, failures, correctness assessment,
expiry, provenance/canonical relation, and reusable lessons. A missing mandatory
per-item field is `ANALYSIS_ERROR`, preserves the safe default, and prevents
bounded completion.
