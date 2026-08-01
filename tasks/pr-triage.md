# PR Triage — 2026-08-01

## Duplicate / twin groups

| Keep | Close | Rationale |
| ---- | ----- | --------- |
| ctrld-sync#1092 | ctrld-sync#1090 | Same `_get_interactive_restart_confirmation` DIM hierarchy; #1092 dims cancel parenthetical only + journal |
| email-security-pipeline#1395 | email-security-pipeline#1398 | Same codeql upload-sarif 2.26.2 bump; #1395 SHA-pins (preferred) |

## Overlap clusters (escalate / Phase 2 — do not auto-close)

- Hydrograph #445 / #448 / #450 — overlapping `validate_data.py` path/file-write Sentinel fixes
- Seatek #555 / #568 / #571 / #573 — repository_automation security cluster
- personal-config Palette #1859 + stacked docs #1861–#1863 — CONFLICTING after main movement
- repoprompt-ce #144 / #157 / #158 / #161 — large CONFLICTING a11y/perf/security salvage pile

## Stale (>30 days)

None in this inventory (max age observed ~3d).

## Merge order applied

1. CI/deps: esp#1395 → hg#449 → hg#442 (hg#443 then CONFLICTING — deferred)
2. Routine: pc#1868 → ctrld#1092 → ctrld#1091 → esp#1397 → Seatek#572 → Seatek#574 → hg#451 → series#338 → series#337
3. Closes: ctrld#1090, esp#1398
4. Reviews: escalations + REQUEST_CHANGES + CodeScene trigger on esp#1399
