# PR Triage — 2026-06-20

**Session:** Phase 1 review-and-merge (cron `0 13 * * *`)

## Disposition counts

| Disposition | Count | PRs |
| --- | ---: | --- |
| MERGE | 11 | pc#1298, ctrld#922, ctrld#919, esp#1133, esp#1132, esp#1125, esp#1134, esp#1135, Seatek#339, hg#276, hg#280 |
| CLOSE-DUPLICATE | 1 | ctrld#921 (dup of merged #919) |
| ESCALATE | 2 | pc#1287 (T1 security salvage), pc#1288 (T3 a11y salvage) |
| DEFER | 6 | sc#121, sc#132, rpce#19–22 |

## Duplicate & overlap analysis

### ctrld #919 vs #921 — DUPLICATE (resolved)

- **Overlap:** Identical `main.py` diff (`_display_len` / `_pad_string` for emoji alignment).
- **Winner:** #919 (all checks green, includes `.jules/palette.md` learning note).
- **Loser:** #921 closed — benchmark gate failed on unrelated `validate_hostname` threshold (1.69×), not caused by alignment change.

### series_correction #121 vs #132 — OVERLAP (both deferred)

- **Overlap:** Both touch `scripts/processor.py` with vectorization intent.
- **Action:** #132 is newer/smaller scope; cs-agent posted on #132. #121 has exhausted cs-agent cycles. Prefer human disposition on #132 first; close #121 as superseded once #132 lands.

### repoprompt-ce #19–21 — CONFLICT CLUSTER (deferred to salvage)

- All three DIRTY with large overlapping diffs (~46–48 files).
- Likely post-merge cascade from concurrent Bolt/Palette/Sentinel PRs on `main`.
- Route to Phase 2 salvage; prioritize #19 (CRITICAL Keychain security).

## Security gate notes

| PR | Gate | Notes |
| --- | --- | --- |
| ctrld#922 | PASS | Exception chaining — prevents data leakage |
| hg#276 | PASS | ExcelFile DoS mitigation |
| pc#1287 | PASS (CI) | AppleScript injection fix — **escalated** per salvage trust boundary |
| rpce#19 | n/a (DIRTY) | Keychain accessibility — escalate via salvage |

## Merge ordering applied

1. Security: ctrld#922, hg#276
2. CI/infra: esp#1133
3. Dependencies: esp#1134, esp#1135 (arrived mid-session)
4. Performance/UI/refactor: pc#1298, ctrld#919, esp#1132, esp#1125, Seatek#339, hg#280

## Stale check

No PRs exceeded 30-day threshold. sc#121 at 5 days remains within policy.
