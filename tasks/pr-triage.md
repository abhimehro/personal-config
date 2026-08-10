# PR Triage — 2026-08-10

## Conflicted / DIRTY queue

### email-security-pipeline #1421 — Bolt aiohttp (contaminated)
- **Disposition:** ESCALATE
- Why: workflow pin downgrades, journal/CHANGELOG wipe, `fix_complexity.py` junk; Lesson **0fh** `create_task` drop risk on S6 repo.
- Action: comment posted; no salvage draft.

### series_correction #364 — PBKDF2 iterations
- **Disposition:** ESCALATE
- Why: auth/crypto hard boundary; `dummy_todos.py` (0ef); no hash migration.
- Action: comment posted; no salvage draft.

### repoprompt-ce #196 — TOCTOU (contaminated)
- **Disposition:** ESCALATE
- Why: TOCTOU mixed with Changelog ISO8601 + journals; sibling cluster still open; `main` still `write`+`setAttributes`.
- Action: comment posted; human consolidate one atomic createFile→replaceItem salvage.

## Salvaged / closed

### repoprompt-ce #184 → #227
- Valuable: MCPCommandParserTests + portable `stat` mode assert.
- Contaminant rejected: dropping macOS `skipIf` on release-promotion suite (Lesson **0fp**).
- Original closed as superseded.

### email-security-pipeline #1459
- Jules Daily QA zero-diff → CLOSE no-op.

## Clusters still held (human T1)

| Cluster | Head PRs | Note |
| ------- | -------- | ---- |
| Seatek path-hijack / timeout | #640/#638/#634/#627/#620… | Consolidate absolute `gh` path + timeouts |
| Hydrograph sanitize_filename | #500/#496/#494/#492… | Newline / log-injection; one strongest regex |
| rpce TOCTOU | #217/#223/#214/#210/#201/#196 | One atomic write salvage |
| series auth | #365/#364/#378 | Timing + PBKDF2 |

## Human merge priority (drafts)

1. series [#379](https://github.com/abhimehro/series_correction_project_updated/pull/379) (CLEAN)
2. series [#375](https://github.com/abhimehro/series_correction_project_updated/pull/375) (CodeScene-only)
3. rpce [#227](https://github.com/abhimehro/repoprompt-ce/pull/227) (NEW)
4. rpce [#224](https://github.com/abhimehro/repoprompt-ce/pull/224)
5. rpce [#218](https://github.com/abhimehro/repoprompt-ce/pull/218)

## Docs lineage (0fk)

Stack today's report on [#1954](https://github.com/abhimehro/personal-config/pull/1954) tip (which already contains [#1953](https://github.com/abhimehro/personal-config/pull/1953)). One competing `tasks/*` docs PR lineage.
