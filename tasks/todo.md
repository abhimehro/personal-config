# Session plan — 2026-07-28 (Phase 1 cron) — complete

- [x] Preflight gate PASS 7/7
- [x] Inventory all open automation PRs → `tasks/pr-inventory.md`
- [x] Triage → `tasks/pr-triage.md`
- [x] Merge zero-diff Daily QA (squash)
- [x] Merge green Dependabot patch bumps
- [x] Review/merge safe Bolt/Palette/routine
- [x] Escalate Sentinel/security; REQUEST_CHANGES on 0er/#1792/#535
- [x] Defer draft Phase-2 / CONFLICTING bolt.md siblings
- [x] Post MCP reviews (close API unavailable — 0es)
- [x] Write `pr-review-2026-07-28.md`, update lessons + review-session-reports
- [x] Commit/push docs on `cursor-agent/automated-pr-workflow-3d54` + open PR (#1802)
# ABHI-1549 — Standardize placeholder secrets in templates

**Route:** T2+S+H  
**Trust boundary:** Committed templates must never hold live secrets; only `op://` refs or unmistakably fake `REPLACE_WITH_*` markers.

## Plan

- [x] Audit flagged files + all `*.template` / `*.example`
- [x] Sync legacy `mcp-configs/mcp-servers.template` to `op://` (match canonical `.json`)
- [x] Rewrite `docs/MCP_SECRETS_MANAGEMENT.md` — clear placeholders + prefer `op://`
- [x] Standardize `.env.example` (and related examples) to `REPLACE_WITH_*`
- [x] Document that Windsurf `op://` templates are secure refs, not secrets
- [x] Extend `tests/test_repo_credential_hygiene.sh` for ABHI-1549 regressions
- [x] Verify with grep / quick tests; commit + PR; comment on Linear

## Security considerations

- `op://Personal/...` is intentional 1Password injection syntax — keep it.
- Ambiguous strings like `your_actual_*_here` are the real problem (looks like a filled value).
- Do not weaken generators that inject secrets outside the repo.
