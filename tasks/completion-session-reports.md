# Completion Session Reports

> Append-only log for the Automated PR Completion Agent. The Completion Agent is the only writer. It reads review and salvage reports but must not modify them.

## Run record template

See [`tasks/pr-stage-run-record.example.md`](pr-stage-run-record.example.md). Each run must identify the ledger version read, items reconciled, stale anchors, terminal outcomes, Stage 2 work items, decision packets, retries, failures, and reusable lessons.
