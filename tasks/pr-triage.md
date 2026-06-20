# PR Triage — 2026-06-20

**Mode:** salvage-and-cleanup (Phase 2)\
**Preflight:** PASS\
**Input:** Live GitHub state + deferred tail from `tasks/pr-review-2026-06-19.md`

## Triage matrix (Phase 2)

| Disposition | Count | Action |
| --- | ---: | --- |
| SALVAGE (new draft PR) | 3 | rp #19→#23; #20→#24; #21→#25 |
| CLOSE-SUPERSEDED | 4 | pc #1299; rp #19, #20, #21 |
| CLOSE-DUPLICATE | 1 | sc #132 (overlaps #121) |
| DEFER (Phase 1 / human) | 9 | pc #1287, #1288; cs #928; esp #1136; hg #281–284; sc #121; rp #22 |
| ESCALATE T0 | 0 | — |

## Infra detection

**No whole-repo infra breakage detected.** Benchmark alert on ctrld#928 is a per-PR performance regression gate (1.59× on dedup benchmark), not a shared `main` failure across 4+ PRs.

## Duplicate & overlap analysis

| Group | Keeper | Closed | Rationale |
| --- | --- | --- | --- |
| rp Sentinel Keychain fix | **#23** (salvage) | #19 | DIRTY; one-line accessibility constant only |
| rp Linux test portability | **#24** (salvage) | #20 | DIRTY; Scripts/ changes only |
| rp Palette a11y labels | **#25** (salvage) | #21 | DIRTY; five UI component files only |
| sc Bolt vectorize perf | **#121** | #132 | Overlapping processor.py vectorization; #121 has cs-agent history |
| pc session docs | **agent branch** | #1299 | Draft session-report PR superseded |

## Per-PR notes

### repoprompt-ce #23 — SALVAGE (draft, T1)

Rebuilt from #19 with only `KeychainService.swift` on current `main`. Replaces `kSecAttrAccessibleAfterFirstUnlock` with `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`.

### repoprompt-ce #24 — SALVAGE (draft, T3)

Rebuilt from #20 with only `Scripts/promote_release.sh`, `Scripts/test_local_production_installer.py`, `Scripts/test_release_tooling.py`. Portable zip sizing and Swift skip guards for Linux CI.

### repoprompt-ce #25 — SALVAGE (draft, T3)

Rebuilt from #21 with accessibility labels on five icon-button components. Omitted bundled trunk/jules/workflow noise from original PR.

### personal-config #1287, #1288 — DEFER

Prior-session salvages remain open. All functional checks green; `UNSTABLE` is Trunk Merge Queue checkbox policy, not test failure.

### personal-config #1284 — AUTO-RESOLVED

Closed without merge since 2026-06-19 deferral. No further action.

### ctrld-sync #928 — DEFER

Palette EOF/Ctrl+C handling is MERGEABLE; `benchmark` check failed on 1.59× perf alert vs baseline. Human disposition — may merge with benchmark waiver or re-run.

### email-security-pipeline #1136 — DEFER (Phase 1)

CLEAN, all checks green. Palette styling on config template output. Phase 1 merge candidate (salvage agent does not merge).

### Hydrograph #281–284 — DEFER (Phase 1)

Four CLEAN dependabot GitHub Actions bumps. Phase 1 merge candidates.

### series_correction #121 — DEFER

Canonical Bolt vectorization PR. CodeScene still failing after multiple cs-agent cycles. No new salvage branch.

### repoprompt-ce #22 — DEFER

Bolt ISO8601DateFormatter cache. Style + dependency-review failing; not DIRTY. Await CI or human fix.
