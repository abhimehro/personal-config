# PR Triage — 2026-08-09

Phase 1 classification retained below. Phase 2 deep-dive dispositions follow.

## Phase 2 decision tree (CONFLICTING only)

| PR | Value on main? | Worth keeping? | Disposition | Why |
| -- | -------------- | -------------- | ----------- | --- |
| series#372 | Partial | Yes (2 log sites) | SALVAGE #379 | Drop format-noise tests |
| series#364 | No real prod auth | Auth demo only | ESCALATE | Hard boundary; `dummy_todos.py` |
| rpce#186 | Partial suite exists | Yes (edge tests) | SALVAGE #224 | Extend canonical file (0fo) |
| rpce#220 | Related #222 merged | No (incomplete) | CLOSE no-op | Missing `isoFormatter` defs |
| esp#1421 | Unique aiohttp | Yes but unsafe | ESCALATE | 0fh / security repo |

## Phase 1 classification summary

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
5. **rpce TOCTOU** — #196/#201/#210/#214/#217/#223 → ESCALATE consolidate.
6. **Docs tasks/** — Phase 2 stacked on Phase 1 #1953 tip (0fk).
7. **rpce REPL tests** — #186 duplicate class path → salvage into Interactive/ (0fo).

## Gates applied (Phase 2)

- Never autonomous merge (S1)
- Never force-push
- Never implement auth/PBKDF2 without human approval
- Never salvage esp#1421 create_task fire-and-forget (0fh)
- Skip `request_reviewers` when author is already `abhimehro` (0ew)
- One competing `tasks/*` docs lineage (stack on #1953) (0fk)
