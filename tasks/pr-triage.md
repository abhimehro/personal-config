# PR Triage — 2026-08-15

## Duplicate / overlap groups

### Hydrograph Bolt `np.where` / `to_numpy`
Merged [#518](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/518). Closed #517 (scratch patch files), #513, #511.

### email-security-pipeline Palette timer
Merged [#1469](https://github.com/abhimehro/email-security-pipeline/pull/1469) (`.jules`). Closed #1480/#1476 (`.Jules/` — lesson 0fe).

### email-security-pipeline header subset
Merged [#1478](https://github.com/abhimehro/email-security-pipeline/pull/1478). HOLD #1487 (`patch_bumpy2.py` hitchhiker, 0fg).

### ctrld pluralize
Merged [#1168](https://github.com/abhimehro/ctrld-sync/pull/1168). Closed CONFLICTING salvage #1159.

### personal-config docs `tasks/*` cascade (0fk)
Recovered `pr-review-2026-08-08.md` … `2026-08-13.md` plus lessons 0fo/0fp/0fl/0fm/0fq onto `cursor-agent/automated-pr-workflow-864b`. Closed Phase 1 cascade [#1986](https://github.com/abhimehro/personal-config/pull/1986). Left Phase 2 salvage docs #1988/#1979 open.

### personal-config `str.join` Bolt cluster
#1997 / #1996 / #1985 / #1978 (+ #1984 set-lookup). HOLD overlapping twins (0fo). Do not merge all.

### Seatek Sentinel read/encoding cluster
#667 / #665 / #662 / #657 — ESCALATE; Phase 2 pick one head.

### repoprompt-ce TOCTOU cluster
#250 / #243 / #239 — ESCALATE; pick one head after human review.

### repoprompt-ce a11y
Merged #235. HOLD #253 (failing Build and Test shards) and #247 (`patch_formatter.py`).

### gh-aw 0.85.4 → 0.86.2
Merged SHA-pinned setup/setup-cli twins (pc #1992/#1993, ctrld #1171, esp #1484/#1485). HOLD ctrld #1170 floating tag on generated `agentics-maintenance.yml`.

## Stale (>30 days)
None in this auto inventory (all younger than 30 days). Oldest security hold: pc #1907 CORS (still escalate, not stale-close).

## Security gate → never merge in Phase 1
- CORS: pc #1907
- All Sentinel-labeled PRs (injection, TOCTOU, spreadsheet, YAML fail-open)
- Workflow consolidations: pc #2002, esp #1471
- Major runtime bumps: seatek #661 numpy 1.26→2.5.2; series #393 numpy span; series #386 pandas 3; esp #1444 opencv 5; ctrld #1136 mypy 2
- Human OOS: pc #1969, ctrld #1165

## Auto-fix attempted
Hydrograph #509 local lockfile merge was discarded after Dependabot force-updated the branch (lesson 0fr). Remote tip squash-merged instead. No force-push.
