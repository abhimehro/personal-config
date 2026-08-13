# PR triage — 2026-08-13

## Duplicate / overlap groups

| Keep | Close/hold siblings | Rationale |
| ---- | ------------------- | --------- |
| pc **#1984** | #1985, #1978 | Three-way `generate_report.py` overlap. #1984 is the only single-file, journal-free, behavior-preserving change. #1985 also duplicates #1982 yaml skipIf. #1978 prepends `.jules/bolt.md` (not append-only). |
| pc **#1982** (rework) | yaml portion of #1985 | Competing skipIf implementations. Prefer fail-loud (pyyaml is required) over skip. |
| rpce **#235** | #226 | Focused a11y labels vs 60-file Palette scope+failing CI. Prefer #235. |
| rpce TOCTOU head **#239** (after CI) | #232, #228 | Huge 290-file TOCTOU PRs vs focused 3-file #239. Hold all (security + failing CI / journal). Do not merge any this pass. |
| rpce DateFormatter | #241, #236, #231 | Same GitService formatter cluster. #231 already CHANGES_REQUESTED; #241/#236 failing CI. |
| Seatek QA **#664** | — | Zero-diff; close. |
| series QA **#384** | — | Zero-diff; close. |
| rpce QA **#240** (then #234) | #234 | Zero-diff QA. #234 also has unrelated shard failures. |

## Stale (>30d)

None of the open automation PRs are older than 30 days.

## Superseded / zero-diff

- Seatek #664, series #384, rpce #240, rpce #234: `changedFiles=0`.

## Security / trust-boundary (always escalate)

- Sentinel: pc #1980, #1907; ctrld #1156; Seatek #665, #662, #657; rpce #239, #232, #228; Hydro salvage #507
- Majors: ctrld #1136 mypy 2.x; esp #1444 opencv 5; Seatek #661 numpy 1→2; series #386 pandas 3; series #385 numpy 2.2→2.5
- Workflow/Gitleaks: pc #1969
- Scratch `/etc/shadow` probe in ctrld #1156 `test_json.py` (Lesson 0fg)

## Salvage drafts (never merge this phase)

pc #1979, ctrld #1159, Hydro #507, rpce #237, series #375, rpce #227
