# ABHI-1321 — Audit and consolidate GitHub workflows

## Approach

Inventory `.github/workflows/` (25 YAML files), identify redundant/disabled/obsolete
workflows, remove safe duplicates, and rewrite README as the canonical catalog.

**Trust boundary:** Workflow YAML controls Actions permissions and secrets access.
Removals reduce attack surface; keep security gates (security-scan, dependency-review).

**Security:** Do not weaken secret scanning, CodeQL, or dependency review. Prefer
removing disabled/stub workflows over merging active security jobs.

## Checklist

- [x] Inventory workflows + GitHub run/state evidence
- [x] Remove redundant `shellcheck.yml` (covered by `mac-audit.yml`)
- [x] Remove stub `test-refactoring-agent.yml` (doubles `/cs-agent` runs)
- [x] Remove disabled Gemini suite (`gemini-*.yml`, 6 files)
- [x] Update `mac-audit/README.md` badge/refs
- [x] Rewrite `.github/workflows/README.md` catalog of remaining workflows
- [ ] Commit, push, open draft PR; update Linear ABHI-1321
- [ ] Verify no broken refs in tests/docs; run smoke tests if needed

## Removal rationale (evidence)

| File | Reason |
| --- | --- |
| `shellcheck.yml` | Same `mac-audit/**` ShellCheck as `mac-audit.yml` job |
| `test-refactoring-agent.yml` | Stub echo-only; fires alongside real agent on `/cs-agent` |
| `gemini-*.yml` (6) | All `disabled_manually` since 2026-07-03; README already optional |

## Result

**25 → 17** workflow YAML files. Security gates retained.

## Kept (documented in README)

Core CI, security, repo automation, CodeScene agent, Jules, label/stale/release helpers.
