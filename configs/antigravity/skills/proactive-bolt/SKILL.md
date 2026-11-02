---
name: proactive-bolt
description: Measurable performance and idempotency optimization reusing per-repo .jules/bolt.md memory, with mandatory numeric-equivalence gates for scientific repositories.
---

# Proactive Bolt (Performance and Idempotency Lens)

Identify and validate **one** measurable performance, resource-efficiency, or
idempotency improvement per run without altering observable behavior.

## Mandatory Research-Repository Numeric Equivalence Gate

For scientific and sensor-analysis repositories
(`Hydrograph_Versus_Seatek_Sensors_Project`, `Seatek_Analysis`, and
`series_correction_project_updated`), vectorization, caching, or I/O changes
must never silently shift scientific outputs:

1. Capture baseline outputs from the unmodified base commit before editing
   production code.
2. Verify numeric equivalence against baseline outputs using consistent
   floating-point tolerances across Python and R:
   - **Python (`NumPy` / `pandas`):**
     `np.allclose(actual, expected, rtol=1e-10, atol=1e-12, equal_nan=True)` or
     `pd.testing.assert_frame_equal(actual, expected, check_exact=False, rtol=1e-10, atol=1e-12)`.
   - **R (`testthat`):**
     `testthat::expect_equal(actual, expected, tolerance = 1e-10)`.
   - **Physical and numerical rationale:** Vectorized BLAS/SIMD reductions
     reorder IEEE-754 floating-point summations (`~1e-15` to `1e-13` rounding
     drift), whereas Seatek ultrasonic bed-elevation sensors and NAVD88 survey
     hydrographs have physical measurement resolution near `10^-4` m
     (sub-millimeter). Pinning `1e-10` relative tolerance (`atol=1e-12` near
     zero) avoids false rejections from SIMD summation order while remaining six
     orders of magnitude tighter than physical sensor precision.
3. Pass the equivalence command via `--numeric-check-cmd` when calling
   `proactive-worktree.sh verify --lens bolt`. The verification runner blocks
   (`exit 3`) any Bolt pass on a research repository that omits
   `--numeric-check-cmd`.
4. **Separating Float-Reorder Noise from Real Regressions:** Large reordered
   `pandas`/`numpy` group reductions (`groupby.sum`, multi-axis `einsum`, or
   parallel BLAS reductions) can occasionally drift past `rtol=1e-10` while
   remaining well below `1e-7` with identical shapes, index ordering, and NaN
   masks. If `--numeric-check-cmd` fails strictly due to verified floating-point
   summation-order drift (`1e-10 < max_rel_diff <= 1e-7`, zero NaN/shape/sign
   mismatches), discard the worktree edit (never commit outputs exceeding
   `rtol=1e-10` unattended) and record `Status: CLEAN_NO_OP` with
   `Substatus: FLOAT_REORDER_DRIFT` (including observed `max_rel_diff` and
   `max_abs_diff`) in the digest so pure float-reorder noise is flagged
   separately from logic/gate regressions and does not count against the `< 2`
   gate-failure budget.

## High-Signal Optimization Targets

1. **Shell Automation (`personal-config`):**
   - Replace repeated subshells (`sed`, `awk`, `cut`, `basename`, `dirname`,
     `date`) inside loops with pure Bash parameter expansion or hoisted
     variables.
   - Eliminate redundant `launchctl`, `scutil`, or `git` invocations where state
     can be queried once per run.
2. **Python Pipelines (`ctrld-sync`, `email-security-pipeline`, research
   repos):**
   - Replace row-wise `.iterrows()` / `.apply()` loops with vectorized
     `numpy`/`pandas` operations where numeric equivalence holds.
   - Reuse HTTP sessions (`requests.Session` / pooled clients), precompile hot
     regular expressions, and avoid repeated JSON/file re-parsing.
3. **R Pipelines (`Seatek_Analysis`):**
   - Avoid quadratic `rbind` growth inside loops; preallocate lists/vectors and
     bind once while preserving exact column types, row ordering, and workbook
     formatting.

## Anti-Patterns to Skip

- Micro-optimizations on cold startup paths that save milliseconds at the cost
  of readability.
- Changing CLI flags, public function signatures, log schemas, or rounding
  behavior.
- Editing tamper-evident build, dependency, or test-harness paths (`Makefile`,
  `pyproject.toml`, `uv.lock`, `requirements*.txt`, `setup.cfg`, `tox.ini`,
  `noxfile.py`, `ruff.toml`, `.ruff.toml`, `.python-version`, `DESCRIPTION`,
  `NAMESPACE`, `.Renviron`, `scripts/*`, `Scripts/*`, `conftest.py`, or existing
  test assertions under `tests/*` / `*/tests/*`).

## Execution Workflow

1. Read `<repo>/AGENTS.md` and `<repo>/.jules/bolt.md` so prior optimizations
   and rejected approaches are not repeated.
2. Check open PR file collisions before editing:
   `$HOME/dev/personal-config/scripts/proactive-worktree.sh check-collisions --repo abhimehro/<repo> --file <relpath>`
3. Create an isolated worktree:
   `$HOME/dev/personal-config/scripts/proactive-worktree.sh prepare --repo-path <repo> --lens bolt --mode local`
4. Measure baseline timing or operation counts, apply the minimal change in the
   worktree, and measure after-change timing.
5. Run hardened verification:
   `$HOME/dev/personal-config/scripts/proactive-worktree.sh verify --worktree <worktree_path> --lens bolt [--numeric-check-cmd "<cmd>"]`
   Independently of the numeric gate, `verify` runs a base-relative **semantic
   test-coverage gate**: touched Python files get an AST parse + undefined-name
   (F82) check, and every touched Python test file is AST-diffed against
   `base_sha`. Any lost test class, lost test method, or drop in total test
   count blocks with `exit 2` **even when the suite passes** — an optimization
   that refactors two tests into one must declare the new total with
   `--expected-test-count <n>`. Record `tests_before` / `tests_after` in the
   report.
6. Commit locally on the worktree branch using title prefix
   `⚡bolt: <concise summary>` (do not push during `2B` local-first mode) and
   record before/after metrics in
   `$HOME/.gemini/antigravity/proactive-reports/YYYY-MM-DD-<repo>.md`.
