# PR Triage — 2026-07-26 (final)

## Duplicate / overlap clusters

### Seatek Sentinel env-filter siblings (Lesson 0ej)
- #507, #518, #525 — overlapping subprocess env denylist / filtering order
- Prefer #525 (least churn) if human confirms denylist; avoid #518 if it deletes sentinel history
- Escalate all; Phase 2 consolidates

### Hydrograph validator.py collision
- Merged #416 Bolt `isna` optimize
- #413 became CONFLICTING; also regresses numpy `<2.0` and reverts Bolt — salvage DoS check only

### ctrld-sync
- Merged #1062 Palette; #1060 remains MERGEABLE CLEAN (escalate security)

### email-security
- Merged #1365 zero-diff
- #1366 REQUEST_CHANGES (artifact skew 0er)
- #1362 CONFLICTING TOCTOU → Phase 2

## Disposition final

| Disposition | Count | PRs |
|-------------|------:|-----|
| MERGE | 6 | pc #1780/#1782, cs #1062, esp #1365, Seatek #530, hg #416 |
| REQUEST-CHANGES | 1 | esp #1366 |
| ESCALATE | 7 | cs #1060, esp #1362, Seatek #507/#518/#525/#521, hg #413 |
| CLOSE | 0 | — |
