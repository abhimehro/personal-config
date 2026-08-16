# PR Triage — 2026-08-07

## Duplicate / overlap groups

### Hydrograph sanitize_filename Sentinel cluster

PRs: #484, #483, #478, #475, #473, #468, #466, #459\
Action: ESCALATE all; Phase 2 consolidate strongest sanitizer into one salvage.

### Seatek path-hijack / subprocess timeout Sentinel cluster

PRs: #620, #617, #612, #610, #607, #605, #590, #585, #580, #573\
Action: ESCALATE all; Phase 2 one absolute-path + timeout salvage.

### repoprompt-ce TOCTOU cluster

PRs: #210, #201, #196 (+ salvage drafts #207/#206)\
Action: ESCALATE; prefer salvage without journal wipe (0fc). #201 has huge
deletions.

### personal-config docs tasks/* cascade

PRs: #1912 (merged), #1925/#1930/#1933/#1914 (closed)\
Action: recovered Aug 5/6 reports + lessons 0fg–0fk into this session’s docs PR
(0fk).

### Seatek Bolt POSIXct twins

#621 (merged, focused) vs #615 (closed — workflow scope creep + failing Gate).

### Palette a11y twins (rpce)

#203 (merged, Chat buttons only) vs #211 (REQUEST_CHANGES — XCTSkip flake
masking; now CONFLICTING after #203).

### ctrld Dependabot uv.lock cascade (0fb)

Merged #1132 (pytest-cov) first. Defer #1133–#1135; escalate #1136 mypy 2.x
major.

## Stale (>30 days)

None in this auto inventory (all age ≤6 days).

## Security gate failures → never merge in Phase 1

- Auth: series #364, #365
- CORS: pc #1907
- All Sentinel-labeled PRs
- Major runtime bumps: esp #1444 opencv 5.x; ctrld #1136 mypy 2.x
