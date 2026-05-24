# ELIR Handoff — ABHI-950 Security Remediation Master Tracker (2026-05-24)

## Purpose

This batch establishes a living security remediation status board for Linear **ABHI-950**, closes two concrete gaps called out on the master issue (CWE-94 supply-chain follow-up on `copilot-setup-steps.yml` and CWE-1236 formula injection in PR inventory exports), and links them to the existing May remediation plan.

## Security

- **CWE-94 / supply chain:** `copilot-setup-steps.yml` now pins `actions/setup-python` and `actions/github-script` to immutable commit SHAs (workflow already bound `workflow_dispatch` input via env for script injection).
- **CWE-1236 / formula injection:** `spreadsheet_safety.escape_spreadsheet_formula()` neutralizes attacker-controlled PR titles, branch names, and author logins before they are written into `tasks/pr-inventory.md` tables that may be opened in Excel.
- **Trust boundary:** GitHub PR/issue metadata is treated as untrusted in export paths.

## Failure Modes

| Condition | Consequence | Mitigation |
| --- | --- | --- |
| New export script skips escaping | Formula injection if malicious PR title is merged | Reuse `spreadsheet_safety`; add test cases for new exporters |
| Tracker drifts from reality | False sense of completion on ABHI-950 | Update `tasks/SECURITY_REMEDIATION_TRACKER.md` when closing Linear sub-tasks |
| P0 credential rotation deferred | Live tokens remain valid after exposure | Operator checklist in tracker (manual) |

## Review Checklist

- [ ] Read `tasks/SECURITY_REMEDIATION_TRACKER.md` and confirm P0–P3 statuses match your Linear sub-issues.
- [ ] Run `python3 -m unittest tests.test_spreadsheet_safety tests.test_scratch_inventory`.
- [ ] Confirm `copilot-setup-steps.yml` action SHAs match intended `v6.2.0` / `v9.0.0` releases.
- [ ] Spot-check a generated `tasks/pr-inventory.md` row whose title starts with `=` — cell should show a leading `'` in the Notes column.

## Maintenance

- Master tracker path: `tasks/SECURITY_REMEDIATION_TRACKER.md` (link from Linear ABHI-950).
- Remaining P1 supply-chain work: `rg 'uses:.*@v[0-9]' .github/workflows` — many Gemini workflows are ratcheted; `code-quality.yml` / automation workflows still use version tags.
