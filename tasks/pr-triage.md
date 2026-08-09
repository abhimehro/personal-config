# PR Triage — 2026-08-09

## Classification summary

| Category | Count (approx) | Action bias |
| -------- | -------------: | ----------- |
| SECURITY / Sentinel | ~30 | ESCALATE (clusters) |
| DEPENDENCY | 4 | Merge minors; escalate majors; one lock/pass |
| PERFORMANCE / Bolt | 4 | Merge green non-security; strip scratch |
| UI / Palette | 3 | Prefer fixed-width twin; close overlap |
| CI/INFRA / Daily QA | 4 | Merge zero-diff; RC failing builds |
| REFACTOR (Devin) | 1 | DEFER human skim |
| Docs (session) | 2 | Recover → close (0fk) |

## Duplicate / overlap groups

1. **Seatek Bolt set()** — #630 vs #635 → merge #635, close #630.
2. **esp Palette timers** — #1447 vs #1451 → merge #1451, close #1447.
3. **Seatek Sentinel path/subprocess** — many siblings → ESCALATE consolidate.
4. **Hydrograph sanitize_filename** — many siblings → ESCALATE consolidate.
5. **rpce TOCTOU** — #196/#201/#210/#214/#217 → ESCALATE consolidate.
6. **Docs tasks/** — #1946/#1947 → recover Aug 8 artifacts, close both.

## Auto-fix applied

| PR | Fix |
| -- | --- |
| esp#1453 | Deleted `patch_extract_headers{3,4,_fix}.py` (Lesson 0fg); CI re-green; merged |

## CodeScene triggers

| PR | Action |
| -- | ------ |
| series#372 | Posted `/cs-agent skill:fix-code-health-degradations` |

## Gates applied

- Never force-push
- Never merge failing required CI
- Never autonomously merge salvage drafts (#375, #218)
- Never merge auth/CORS/Sentinel trust-boundary without human
- One `uv.lock` Dependabot merge this pass (#1133); #1135 deferred
