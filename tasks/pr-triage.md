# PR Triage — 2026-08-06 Phase 1

Decision tree per `docs/automated-pr-review-agent.md`. Mode: review-and-merge.
Adversarial parallel review: `claude-opus-4-8-thinking-high` + `gpt-5.5-high`.

## Disposition summary

| Disposition | Count | Notes |
| ----------- | ----: | ----- |
| MERGED (squash) | 13 | deps, pins, Bolt/Palette, tests-only, autofix |
| CLOSED | 2 | rpce#200 superseded; rpce#192 journal wipe + mass deletes |
| AUTOFIX | 1 | esp#1423 risk casing (Lesson **0fi**) |
| REQUEST_CHANGES | ~10 | yaml silent fail; 0ff test/prod renames; 0fg artifacts; failing CI |
| ESCALATE | ~22 | Sentinel clusters; CORS; SSRF allowlist; fire-and-forget alerts; PBKDF2 |
| DEFER / HOLD | remainder | docs PRs; salvage; CONFLICTING; Code Health refactors |

## Merge batch (ordered)

1. series#368 Dependabot `pnpm/action-setup` SHA pin (verified upstream)
2. hg#476 Dependabot `pandas-stubs` (CI stubs only)
3. pc#1928 / esp#1433 `github/gh-aw` action pin v0.85.4 (verified)
4. ctrld#1121 Palette grammar; #1122 Bolt try/except (journal append-only)
5. Seatek#613 Bolt `.subset2` / `mean.default`
6. rpce#198 a11y; #199 `keys.contains`; #204 DateFormatter static
7. pc#1909 tests-only `write_lists`; Seatek#596 tests-only `_hotspot_line_count`
8. esp#1423 after autofix cycle 1 (case-insensitive risk match) + green CI

## Security / escalate clusters (Phase 2 input)

- **Hydrograph sanitize:** #459/#466/#468/#473/#475/#478
- **Seatek subprocess Sentinels:** #573/#580/#585/#590/#605/#607/#610/#612
- **esp security:** #1431 SSRF host allowlist; #1432 email/subprocess validators; #1421 create_task alerts (0fh)
- **pc#1907** CORS allowlist + stray `handoff.md`
- **series#365/#364** auth timing / PBKDF2 (CS red on #364 — `/cs-agent` posted)
- **rpce TOCTOU Sentinels** #196/#201 (CI red; escalate even if greened)

## Duplicate / close

- rpce#200 closed after #204 (same DateFormatter change; harness churn conflict)
- rpce#192 closed: Keychain claim + `.jules/bolt.md` wipe + mass test deletions (0fc)

## Autofix detail

**esp#1423:** Production `risk_level` is lowercase (`high`/`medium`/`low`). PR
matched `risk=HIGH`. Autofix uses case-insensitive substring match; tests use
production lowercase + one uppercase regression case. Local 19/19
`test_logging_utils.py` pass; CI green; squash-merged.

## Phase 2 trigger

**Yes** — ≥1 ESCALATE; Hydrograph sanitize cluster; Seatek Sentinel cluster;
rpce CONFLICTING salvage/security tail; series CodeScene red.
