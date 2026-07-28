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
