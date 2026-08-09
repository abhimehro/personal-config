# PR Inventory — 2026-08-09

Phase 1 cron (13:00 UTC) + Phase 2 salvage (17:00 UTC).
Preflight PASS. Auth: `abhimehro` PAT. Merge policy: squash (Phase 1 only);
Phase 2 never merges (S1).

## Phase 2 live CONFLICTING/DIRTY (start)

| Repo | PR | Author shape | Disposition |
| ---- | -- | ------------ | ----------- |
| email-security-pipeline | 1421 | Bolt/aiohttp | ESCALATE (0fh) |
| repoprompt-ce | 220 | Jules Daily QA | CLOSE no-op |
| repoprompt-ce | 186 | Jules tests | SALVAGE → #224 |
| series_correction… | 372 | Sentinel logging | SALVAGE → #379 |
| series_correction… | 364 | Sentinel PBKDF2 (dummy) | ESCALATE |

## Phase 2 salvage drafts opened

| Repo | New PR | Salvages | Verify |
| ---- | ------ | -------- | ------ |
| series_correction… | [#379](https://github.com/abhimehro/series_correction_project_updated/pull/379) | #372 | `pytest scripts/tests/test_batch_correction.py` → 20 passed |
| repoprompt-ce | [#224](https://github.com/abhimehro/repoprompt-ce/pull/224) | #186 | `make dev-test FILTER=REPLInputParserTests` (macOS) |

## Prior salvage drafts still open (human)

| Repo | PR | Note |
| ---- | -- | ---- |
| series_correction… | [#375](https://github.com/abhimehro/series_correction_project_updated/pull/375) | Aug 8 — `_ensure_output_directory` OSError |
| repoprompt-ce | [#218](https://github.com/abhimehro/repoprompt-ce/pull/218) | Aug 8 — ToolGroupsCatalog tests |

## Phase 1 start/end (unchanged context)

| Repo | Auto open (Phase 1 start) | Notes after Phase 2 |
| ---- | ------------------------: | ------------------- |
| personal-config | 4 → 2 | #1953 docs + #1907 CORS |
| ctrld-sync | 5 → 4 | majors/Sentinel held |
| email-security-pipeline | 6 → 2 | #1421 escalate; #1444 opencv |
| Seatek_Analysis | 16 → ~14 | Sentinel cluster |
| Hydrograph… | 12 → 12 | sanitize cluster |
| series_correction… | 5 → ~4 | #372 closed; #379 draft; #364/#365/#375 |
| repoprompt-ce | 10 → ~8 | #186/#220 closed; #224 draft; TOCTOU + #218 |

## Phase 1 merged / closed

See Phase 1 section in `tasks/pr-review-2026-08-09.md` (11 merged, 5 closed).

## Representative remaining (post Phase 2)

| Repo | PR | Disposition |
| ---- | -- | ----------- |
| personal-config | 1907 | ESCALATE CORS |
| personal-config | 1953 | Phase 1 docs draft (stack base) |
| ctrld-sync | 1135/1136/1145/1147 | DEFER / ESCALATE |
| email-security-pipeline | 1421/1444 | ESCALATE |
| Seatek_Analysis | 573…634 | ESCALATE Sentinel cluster |
| Hydrograph… | 459…492 | ESCALATE sanitize cluster |
| series… | 364/365 | ESCALATE auth |
| series… | 375/379 | Salvage drafts — human only |
| repoprompt-ce | 196…217/223 | ESCALATE TOCTOU |
| repoprompt-ce | 218/224 | Salvage drafts — human only |
