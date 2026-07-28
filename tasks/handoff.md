# ELIR Handoff — ABHI-1549 Placeholder Secrets

## 📋 Purpose

Standardize committed placeholder markers so scanners and humans cannot confuse
templates with live credentials. MCP templates keep `op://` 1Password CLI refs;
`.env.example`-style files use `REPLACE_WITH_*` markers; docs no longer say
`your_actual_…`.

## 🛡️ Security

- **Threats addressed:** Ambiguous placeholders mistaken for real keys; legacy
  `YOUR_*_API_KEY` MCP template diverging from the canonical `op://` source of
  truth; docs implying filled credentials belong in-repo.
- **Assumptions:** No live keys were present in the flagged files (confirmed by
  audit). Windsurf `op://` values are intentional secure refs.
- **Trust boundary:** Committed templates vs generated/local configs outside
  git.

## ⚠️ Failure Modes

| Break                                      | Consequence                         | Mitigation                                      |
| ------------------------------------------ | ----------------------------------- | ----------------------------------------------- |
| Someone pastes a live key into a template  | Key lands in git                    | Generator + hygiene test; regenerate with `op`  |
| Legacy template drifts from canonical JSON | Conflicting docs / scanner noise    | Legacy file now mirrors `.template.json`        |
| Scanner still flags `op://`                | False positive                      | Documented as secure-storage refs in MCP docs   |

## ✅ Review Checklist

- [ ] Confirm `mcp-configs/mcp-servers.template` == `mcp-servers.template.json`
- [ ] Confirm Windsurf templates still use only `op://` (not live keys)
- [ ] Skim `docs/MCP_SECRETS_MANAGEMENT.md` placeholder convention table
- [ ] `bash tests/test_repo_credential_hygiene.sh` passes

## 🔧 Maintenance

- Edit **only** `mcp-configs/mcp-servers.template.json`, then copy/sync the
  legacy `.template` mirror (or regenerate via the same content).
- New env examples must use `REPLACE_WITH_*`, never `your_actual_*`.
- Keep `scripts/generate-mcp-configs.sh` as the path that resolves secrets
  outside the repo.
