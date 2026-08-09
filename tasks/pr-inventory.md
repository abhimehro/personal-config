# PR Inventory — 2026-08-09

Phase 1 cron (13:00 UTC). Preflight PASS 7/7. Auth: `abhimehro` PAT.
Mode: review-and-merge. Stale threshold: 30 days. Merge: squash.

Scope: automation-driven open PRs (bot authors + human-authored
Bolt/Jules/Sentinel/Palette/salvage/cursor-agent/Dependabot).

## Start-of-session counts (auto targets)

| Repo | Auto open |
| ---- | --------: |
| personal-config | 4 |
| ctrld-sync | 5 |
| email-security-pipeline | 6 |
| Seatek_Analysis | 16 |
| Hydrograph… | 12 |
| series_correction… | 5 |
| repoprompt-ce | 10 |
| **Total** | **~58** |

## End-of-session open remainder (auto, approx)

| Repo | Open | Notes |
| ---- | ---: | ----- |
| personal-config | 1 | #1907 CORS ESCALATE |
| ctrld-sync | 4 | #1135 lock deferred; #1136 mypy; #1145 Devin; #1147 Sentinel |
| email-security-pipeline | 2 | #1421 CONFLICTING; #1444 opencv |
| Seatek_Analysis | ~12 | Sentinel path/subprocess cluster |
| Hydrograph… | 12 | Sentinel sanitize_filename cluster |
| series_correction… | 4 | #364/#365 auth; #372 CodeScene; #375 salvage draft |
| repoprompt-ce | ~7 | TOCTOU + failing CI #186/#220 + salvage #218 |
| **Approx open auto** | **~42** | |

## Merged this session (11)

| Repo | PR | Category | Note |
| ---- | -- | -------- | ---- |
| email-security-pipeline | 1454 | CI/INFRA | zero-diff Jules Daily QA |
| Seatek_Analysis | 633 | CI/INFRA | zero-diff Jules Daily QA |
| series_correction… | 377 | CI/INFRA | zero-diff Jules Daily QA |
| personal-config | 1949 | SECURITY/DEPS | pin pyyaml==6.0.3 |
| ctrld-sync | 1133 | DEPENDENCY | pre-commit (one uv.lock / 0fb) |
| repoprompt-ce | 221 | UI | Palette a11y labels |
| email-security-pipeline | 1451 | UI | Palette fixed-width timers |
| Seatek_Analysis | 635 | PERFORMANCE | Bolt data.table set() |
| repoprompt-ce | 222 | PERFORMANCE | Bolt static ISO8601DateFormatter |
| email-security-pipeline | 1453 | PERFORMANCE | Bolt header parse (+ autofix strip scratch) |

## Closed this session (5)

| Repo | PR | Reason |
| ---- | -- | ------ |
| Seatek_Analysis | 630 | Duplicate of #635 (narrower twin) |
| email-security-pipeline | 1447 | Superseded by #1451 (ui.py CONFLICTING) |
| personal-config | 1946 | Docs cascade 0fk; Aug 8 report recovered |
| personal-config | 1947 | Docs cascade 0fk; salvage summary recovered to memory |

## Representative remaining (disposition)

| Repo | PR | Disposition |
| ---- | -- | ----------- |
| personal-config | 1907 | ESCALATE CORS |
| ctrld-sync | 1135 | DEFER lock (0fb) |
| ctrld-sync | 1136 | ESCALATE mypy 2.x |
| ctrld-sync | 1145 | DEFER large Devin refactor |
| ctrld-sync | 1147 | ESCALATE Sentinel PRNG |
| email-security-pipeline | 1421 | ESCALATE/CONFLICTING aiohttp |
| email-security-pipeline | 1444 | ESCALATE opencv major |
| Seatek_Analysis | 573…634 | ESCALATE Sentinel cluster |
| Hydrograph… | 459…492 | ESCALATE sanitize cluster |
| series… | 364/365/372 | ESCALATE auth / CodeScene |
| series… | 375 | Salvage draft — no auto-merge |
| repoprompt-ce | 196…217 | ESCALATE TOCTOU |
| repoprompt-ce | 186/220 | REQUEST_CHANGES failing CI |
| repoprompt-ce | 218 | Salvage draft — no auto-merge |
