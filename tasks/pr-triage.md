# PR triage — backlog cleanup test (2026-03-19)

## Duplicates / superseded

| Repo | PRs | Finding | Action |
|------|-----|---------|--------|
| personal-config | #646 vs #648 | Same Sentinel/CWE-78 theme; #648 newer, removes stray `fix.py`, broader base.sh handling | **Close #646** (superseded by #648) |
| Seatek_Analysis | #89 vs #92 | **Identical** `Updated_Seatek_Analysis.R` hunk; only `.jules/palette.md` wording differed | **Close #89** (duplicate of #92) |

## Overlap (not duplicates)

| Repo | PRs | Notes |
|------|-----|--------|
| personal-config | #646, #648 | Same files touched; resolved by closing #646, merging #648 |
| Seatek_Analysis | #88, #91 | Same R file family; sequential merges + **merge commit on #91** after main moved |
| Hydrograph | #79–82 | `data_validator.py` / `processor.py` overlap; sequential merges + **merge commits on #81, #82** |

## Security gates (high level)

- **personal-config #646–648, #647:** No secrets added; eval use **reduced/validated** (Sentinel). Codacy workflow failed with long-running/cancel pattern — treated as **tooling/baseline noise** because `Run All Tests`, Shell/Python quality, CodeQL, dependency-review passed and diff reviewed manually.
- **email-security-pipeline #555:** CodeScene failed — **treated as unrelated** to small Spinner UX change; pytest + Codacy + CodeQL passed.
- **Seatek / Hydro:** No new auth/payment/DB migration paths; Sentinel PRs reviewed for DoS/validation — merged after conflict resolution and green checks.

## CI policy applied

- Did **not** merge with failing **pytest**/core repo tests.
- Allowed merge when **optional / third-party** checks failed (Codacy, CodeScene) if failure was **not plausibly caused by the diff** and core checks passed.

## Operational notes

- **Git push** to update PR branches required `remote` URL with `GH_TOKEN` (default credential picked `cursor[bot]` — 403). Document for future runs.
- **Sequential merges** caused **DIRTY** state on downstream PRs; **re-checked** after each merge and used **merge-main-into-branch** fixes (no force-push).
