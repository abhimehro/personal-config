# ELIR: Explain Like I'm Reviewing

**PURPOSE:**
This PR introduces a centralized `.shellcheckrc` file at the repository root to manage project-wide ShellCheck exclusions (such as SC1091). This significantly reduces warning noise and provides a scalable alternative to inline comments, aligning with the audit effort detailed in #447 and #446.

**SECURITY:**
No new vulnerabilities are introduced. We strictly enforce that warnings such as `SC2034` (unused variables) are NOT globally disabled, ensuring unused variables continue to be flagged for review to prevent silent regressions or logic errors.

**FAILS IF:**
If developers assume Trunk's integrated ShellCheck reads the repo‑root `.shellcheckrc`. Trunk instead uses `.trunk/configs/.shellcheckrc` as its authoritative configuration, so the root file only affects direct `shellcheck` CLI runs (and even then is ignored when `--norc` is provided).

**VERIFY:**
- Ensure `.shellcheckrc` only disables `SC1091`.
- Ensure `SC2034` is present but commented out, keeping the warnings visible for individual review.
- Confirm that running `shellcheck` from the repository root (without `--norc`) respects the `.shellcheckrc` exclusions, and that `trunk check` behavior remains governed by `.trunk/configs/.shellcheckrc`.

**MAINTAIN:**
Any new global exclusions must be added directly to this file, with explicit rationale as a comment above the `disable=` directive. Ensure not to broadly disable real logical bugs.
