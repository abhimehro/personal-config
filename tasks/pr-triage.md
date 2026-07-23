# PR Triage — 2026-07-23

## MERGE (squash, delete branch)

Order: deps → UI/a11y → routine perf → then re-check siblings.

| Repo | PR | Rationale |
|------|-----|-----------|
| personal-config | 1753 | Patch bump codeql-action floating tags (already unpinned style); CI green |
| personal-config | 1752 | Palette a11y `th scope=row`; no logic risk |
| Hydrograph… | 402 | pre-commit CI upper-bound widen; CI green |
| Hydrograph… | 404 | Private helper Series→dict; single caller updated |
| series_correction… | 286 | ruby/setup-ruby SHA pin refresh (keeps pin) |
| Seatek_Analysis | 515 | matplotlib floor raise only (optional Series_27) |
| email-security-pipeline | 1344 | Fast-path `'http' in` before `https?://` regex; lowercased text |
| repoprompt-ce | 138 | accessibilityLabel on icon buttons only |

## CLOSE

| Repo | PR | Reason |
|------|-----|--------|
| personal-config | 1751 | Zero-diff QA Check |
| Seatek_Analysis | 517 | Zero-diff Jules Daily QA |

## ESCALATE (human; do not merge)

| Repo | PR | Reason |
|------|-----|--------|
| personal-config | 1744 | CONFLICTING; Action SHA→floating tag unpin (0eh) |
| personal-config | 1721 | CONFLICTING; GH_TOKEN/env cache near detect_duplicates |
| email-security-pipeline | 1328 | Secrets TOCTOU/chmod (prior escalate) |
| email-security-pipeline | 1324 | Auth-Results scoring surface |
| email-security-pipeline | 1319 | gh_token_cli write path |
| email-security-pipeline | 1327 | CONFLICTING + CodeScene; broad SPF Bolt |
| Seatek_Analysis | 518 | Subprocess env filter trust boundary (new Sentinel) |
| Seatek_Analysis | 507 | Same surface as #518 (overlap); prior escalate |
| Seatek_Analysis | 514 | pandas 2→3 major |
| Seatek_Analysis | 511 | Path/IO security refactor + Trunk fail |
| series_correction… | 285 | dummy_todos + CodeScene fail (0ef) → post cs-agent |
| series_correction… | 276 | dummy_todos DoS (0ef) |
| series_correction… | 275 | auth+DoS + CONFLICTING (0ef) |
| series_correction… | 268 | dummy_todos cluster (0ef) |
| repoprompt-ce | 126 | download-artifact tip major (0dw) |
| repoprompt-ce | 127 | upload-artifact tip major (0dw) |

## DEFER

| Repo | PR | Reason |
|------|-----|--------|
| personal-config | 1749 | Draft Phase 2 docs salvage — human merge only |
| personal-config | 1748 | Draft visual-recap salvage (token sanitize) — human |
| email-security-pipeline | 1342 | Draft Phase 2 salvage #1330 |
| email-security-pipeline | 1341 | Draft Phase 2 salvage #1335/#1314 |
| email-security-pipeline | 1320 | Prior REQUEST-CHANGES: test reduced to `pass` |

## Overlaps

- Seatek #518 ≈ #507 (both reorder `filter_env_securely` custom_env merge). Prefer human pick of #518 (newer/simpler) or consolidated salvage; do not auto-close #507 without human ack.
- series_correction #268/#275/#276/#285 share `dummy_todos.py` — leave cluster for Phase 2/human.
