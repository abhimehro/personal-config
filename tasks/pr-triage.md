# PR Triage — 2026-07-18 Phase 2 (FINAL)

## Duplicate / overlap

- Phase 1 docs [#1685](https://github.com/abhimehro/personal-config/pull/1685) folded into this salvage session PR (same artifact set + Phase 2 addendum).

## Stale (>30d)

None.

## Conflict deep-dive — pc#1670

| Item | Finding |
|------|---------|
| Merge state | `CONFLICTING` / `DIRTY` after [#1679](https://github.com/abhimehro/personal-config/pull/1679) |
| Conflict class | **modify/delete** on `.github/workflows/shellcheck.yml` |
| PR intent | Delete standalone `shellcheck.yml` (claims covered by `mac-audit.yml` / `code-quality.yml` / `security-scan.yml`) + remove Gemini suite + gitleaks tweak |
| `main` after #1679 | `shellcheck.yml` **kept and enhanced** (cached `setup-shellcheck` action) |
| Trust boundary | Deletes `gemini-*.yml`, edits `.github/gitleaks.toml`, removes agent workflows — **S6 / human gate** |
| Salvage decision | **No draft salvage.** Resolving keep-vs-delete of ShellCheck + Gemini removal is a maintainer product decision, not an automation cherry-pick. |

## Escalations (unchanged — human review)

| PR | Severity | Why not salvage |
|----|----------|-----------------|
| [pc#1670](https://github.com/abhimehro/personal-config/pull/1670) | T2 | CI trust boundary + DIRTY |
| [sc#233](https://github.com/abhimehro/series_correction_project_updated/pull/233) | T1 | Auth / password hashing (`dummy_todos.py`) |
| [hg#374](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/374) | T2 | numpy 1.x→2.x major |
| [rpce#126](https://github.com/abhimehro/repoprompt-ce/pull/126) / [#127](https://github.com/abhimehro/repoprompt-ce/pull/127) | T2 | tip-release artifact majors (Lesson 0dw) |

## Dispositions executed (Phase 2)

### SALVAGE drafts opened: 0

### CLOSED: 1 (docs fold)

- pc#1685 → superseded by this session docs PR

### ESCALATE carried: 5

See table above. Diagnostic comment posted on #1670.
