# Task: Automated bot PR review session

## Route
- T5+S - Orchestrate with security review

## Trust boundaries
- GitHub API data from `gh` is untrusted input and must be validated before making decisions.
- Remote PR state can change mid-session; mergeability and checks must be re-read before final dispositions.
- Preflight must pass before any inventory, triage, or write-path actions.

## Plan
- [x] Run mandatory preflight with `tasks/pr-review-agent.config.yaml`.
- [x] Collect current open bot PR inventory for each configured repository.
- [x] Classify PRs, identify duplicates/conflicts/stale items, and update `tasks/pr-inventory.md` and `tasks/pr-triage.md`.
- [x] Review top candidates by merge order, record dispositions, and note any trust-boundary escalations.
- [x] Write `tasks/pr-review-2026-03-08.md` with actions, metrics, and ready-to-execute follow-ups.
- [x] Update `tasks/lessons.md` with any new patterns from this session.
- [ ] Verify artifacts, inspect diff, commit, and push changes.
