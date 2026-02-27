# PR Triage Findings

Triage basis: session 2 inventory from `tasks/pr-inventory.md` (2026-02-27).

## Exact Duplicates / High File Overlap

| Repo | PRs | Overlap | Keep | Close | Rationale |
|---|---|---:|---|---|---|
| abhimehro/ctrld-sync | #406, #399 | 1.00 | Neither | Both | Both fail CI with identical pytest-xdist approach; consolidate into fresh PR if feature wanted |
| abhimehro/ctrld-sync | #405, #402, #395 | 0.90 | #395 | #405, #402 | All add test workflow; #395 is superset with uv caching + badge; #402 is a subset; #405 fails CI |
| abhimehro/email-security-pipeline | #381, #372 | 0.85 | #381 | #372 | Both target nested archive detection in media_analyzer; #381 is broader, includes tests, and adds constant |

## Semantic Duplicates

| Repo | PRs | Keep | Close | Rationale |
|---|---|---|---|---|
| abhimehro/ctrld-sync | #401, #400 | Both | — | Complementary CI cache improvements: #401 pins hashes, #400 broadens scope. Merge sequentially: #401 first |
| abhimehro/ctrld-sync | #394, #396 | #396 | #394 | #394 has conflicts and is partially subsumed by #396's dead-code removal |

## Superseded PRs (No Effective Diff vs Base)

| Repo | PR # | Disposition | Rationale |
|---|---:|---|---|
| abhimehro/ctrld-sync | 397 | CLOSE-STALE | Zero changed files — SECURITY.md changes already on main |
| abhimehro/ctrld-sync | 394 | CLOSE-STALE | CONFLICTING/DIRTY + subsumed by #396 |
| abhimehro/email-security-pipeline | 373 | CLOSE-STALE | Zero-diff WIP — no docstrings added |
| abhimehro/email-security-pipeline | 371 | CLOSE-STALE | Zero-diff WIP — no refactoring done |
| abhimehro/email-security-pipeline | 370 | CLOSE-STALE | Zero-diff WIP — no tests added |

## Conflicting PRs

| Repo | PR # | Issue | Action |
|---|---:|---|---|
| abhimehro/personal-config | 385 | CONFLICTING/DIRTY after #384 merge changed shared files | ESCALATE: author rebase needed |
| abhimehro/ctrld-sync | 394 | CONFLICTING/DIRTY on `main.py` and `uv.lock` | CLOSE-STALE: subsumed by #396 |
| abhimehro/email-security-pipeline | 381 | CONFLICTING/DIRTY on `media_analyzer.py` | MERGE-AFTER-FIX: rebase then merge |
| abhimehro/email-security-pipeline | 372 | CONFLICTING/DIRTY on `media_analyzer.py` | CLOSE-DUPLICATE: superseded by #381 |

## Stale Candidates (>30 days inactive and failing CI)

No stale candidates detected under the configured threshold. All bot PRs are 7–12 days old.

## Permission Constraints

| Repo | Merge | Close | Comment | Review |
|---|---|---|---|---|
| abhimehro/personal-config | ✅ | ❌ | ❌ | ❌ |
| abhimehro/email-security-pipeline | ❌ | ❌ | ❌ | ❌ |
| abhimehro/ctrld-sync | ❌ | ❌ | ❌ | ❌ |

All `CLOSE-*` dispositions for non-personal-config repos require human execution or elevated token scopes.

## Ready-to-Execute Human Actions

### ctrld-sync — Close Queue

```bash
# Close duplicates and stale
gh pr close 406 --repo abhimehro/ctrld-sync --comment "Closing: duplicate of parallel pytest work (#399 also fails CI). Consolidate if feature desired."
gh pr close 405 --repo abhimehro/ctrld-sync --comment "Closing: duplicate of test workflow (#395 is superset with uv caching). Use #395 instead."
gh pr close 402 --repo abhimehro/ctrld-sync --comment "Closing: duplicate of test workflow (#395 is superset). Use #395 instead."
gh pr close 399 --repo abhimehro/ctrld-sync --comment "Closing: duplicate of #406, both fail CI. Consolidate if feature desired."
gh pr close 397 --repo abhimehro/ctrld-sync --comment "Closing: zero changed files — SECURITY.md changes already on main."
gh pr close 394 --repo abhimehro/ctrld-sync --comment "Closing: merge conflicts + subsumed by #396 dead-code removal."
```

### ctrld-sync — Merge Queue (recommended order)

```bash
gh pr merge 403 --repo abhimehro/ctrld-sync --squash --delete-branch  # Python 3.13 standardization
gh pr merge 401 --repo abhimehro/ctrld-sync --squash --delete-branch  # Pin CI cache keys
gh pr merge 400 --repo abhimehro/ctrld-sync --squash --delete-branch  # Broaden pip cache keys
gh pr merge 395 --repo abhimehro/ctrld-sync --squash --delete-branch  # Test workflow (best of 3)
gh pr merge 398 --repo abhimehro/ctrld-sync --squash --delete-branch  # README fix
```

### email-security-pipeline — Close Queue

```bash
gh pr close 372 --repo abhimehro/email-security-pipeline --comment "Closing: superseded by #381 (broader fix with tests)."
gh pr close 373 --repo abhimehro/email-security-pipeline --comment "Closing: zero-diff WIP — no docstrings added."
gh pr close 371 --repo abhimehro/email-security-pipeline --comment "Closing: zero-diff WIP — no refactoring done."
gh pr close 370 --repo abhimehro/email-security-pipeline --comment "Closing: zero-diff WIP — no tests added."
```

### email-security-pipeline — Merge Queue (recommended order)

```bash
# Phase 1: Independent PRs
gh pr merge 374 --repo abhimehro/email-security-pipeline --squash --delete-branch  # Static analysis fixes
gh pr merge 368 --repo abhimehro/email-security-pipeline --squash --delete-branch  # TTL cache limits
gh pr merge 369 --repo abhimehro/email-security-pipeline --squash --delete-branch  # Regex compilation
gh pr merge 378 --repo abhimehro/email-security-pipeline --squash --delete-branch  # endswith() fix

# Phase 2: email_parser
gh pr merge 380 --repo abhimehro/email-security-pipeline --squash --delete-branch  # Replace bare excepts

# Phase 3: Analyzer scoring (sequential)
gh pr merge 379 --repo abhimehro/email-security-pipeline --squash --delete-branch  # Risk level extraction
gh pr merge 377 --repo abhimehro/email-security-pipeline --squash --delete-branch  # ThreatScorer utility

# Phase 4: Post-cleanup
# #381 — rebase after closing #372, then merge
# #375 — fix CodeFactor nit, then merge
```

### PRs Requiring Human Review Before Merge

| Repo | PR # | Why |
|---|---:|---|
| abhimehro/ctrld-sync | 407 | `uv.lock` adds `pytest-benchmark` — strip lockfile changes |
| abhimehro/ctrld-sync | 404 | FEATURE: adds `pyyaml` runtime dep + `~/.ctrld-sync/` convention — needs architectural sign-off |
| abhimehro/ctrld-sync | 396 | Removes `return True` from validators — verify no caller depends on truthy return |
| abhimehro/email-security-pipeline | 376 | Refactors body-size limiting (DoS protection) without tests |
| abhimehro/email-security-pipeline | 375 | 639-line test file with CodeFactor nit — minor fix needed |
| abhimehro/personal-config | 385 | CONFLICTING: rebase needed after #384 merge |
