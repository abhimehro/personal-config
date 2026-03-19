# PR Triage — Automated PR Review Agent
**Run date:** 2026-03-19

---

## Triage Classification Key

- **MERGE** — All gates pass, safe to squash-merge
- **CLOSE-DUPE** — Superseded by a newer PR addressing the same code/bug
- **ESCALATE** — Touches auth/payments/migrations/security-sensitive logic OR failing CI
- **HOLD** — Failing CI that is related to the PR changes (needs fix before merge)

---

## personal-config

### PR #648 — 🛡️ Sentinel: [CRITICAL] CWE-78 eval fix (newer)
**Classification: MERGE**

- Files: `maintenance/bin/system_cleanup.sh`, `configs/.config/mole/lib/core/app_protection.sh`, `configs/.config/mole/lib/core/base.sh`, `.jules/sentinel.md`, ~~`fix.py`~~ (deleted)
- Fix: Wraps `eval "$var_name=..."` with `[[ "$var_name" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]` guard
- Deletes leftover `fix.py` scratch file
- CI: All required checks pass. Codacy CANCELLED is a recurring transient issue on this repo — not caused by this PR
- CodeScene: APPROVED
- Gate check: Fixes CWE-78 in shell scripts. Not auth/payments/DB migration. Safe to merge
- **Supersedes PR #646**

### PR #647 — 🎨 Palette: Spinner subprocess optimization
**Classification: MERGE**

- Files: `scripts/bootstrap_fish_plugins.sh`
- Change: Replaces `date +%s` subprocess spawn every 0.1s in spinner loop with iteration counter
- CI: All required checks pass. Codacy CANCELLED — transient, same pattern as #648
- CodeScene: APPROVED
- Gate check: UX improvement only. No security surface. Safe to merge
- No conflict with #648 (different files)

### PR #646 — 🛡️ Sentinel: [CRITICAL] CWE-78 eval fix (older)
**Classification: CLOSE-DUPE**

- Same vulnerability as #648 (same three files, same eval guards), created 1 day earlier
- Approach differences: #646 uses early-return guard pattern; #648 wraps the eval and also cleans up `fix.py`
- #648 is more complete (deletes leftover file, better sentinel.md entry with specific file paths)
- Once #648 is merged, #646 will conflict
- **Action: Close as superseded by #648**

---

## email-security-pipeline

### PR #555 — 🎨 Palette: Improve Spinner Failure Feedback
**Classification: HOLD**

- Files: `src/utils/ui.py`, `src/main.py`, `src/utils/setup_wizard.py`
- Change: Fixes Spinner context manager to show `✘` when `spinner.fail()` is called explicitly (even without exception)
- CI: **CodeScene Code Health Review FAILED** (code health regression detected)
- All other checks pass (bandit, Codacy, pytest, CodeQL, etc.)
- CodeScene review state is COMMENTED (not APPROVED) — flagged a quality gate failure
- Policy: "Never merge failing CI unless the failure is clearly unrelated to the PR"
- This failure IS related to PR changes (CodeScene analyzed the diff)
- **Action: Leave comment for Jules to address the CodeScene feedback before merge**

---

## Seatek_Analysis

### PR #87 — 🛡️ Sentinel: [MEDIUM] Remove stack trace from error response
**Classification: MERGE**

- Files: `Series_27/Analysis/outlier_analysis_series27.py`
- Change: Removes `exc_info=True` from error log calls to prevent stack trace leakage
- CI: CLEAN — all 6 checks pass including CodeScene APPROVED
- Isolated file, no conflicts with other PRs
- Gate check: Information disclosure fix. Safe category

### PR #88 — ⚡ Bolt: data.table aggregation (older)
**Classification: CLOSE-DUPE**

- Files: `Updated_Seatek_Analysis.R` (lines 131–260), `.jules/bolt.md`
- Same code change as PR #91 (both change `data.frame` → `data.table` in the same lines)
- PR #91 is newer and more complete: adds tests in `tests/testthat/test-process_all_data.R`, cleaner `calculate_summary_stats` (uses data.table `:=`), better bolt.md learning note
- Once #91 is merged, #88 will conflict
- **Action: Close as superseded by #91**

### PR #89 — 🎨 Palette: Add empty iterable check to progress bar
**Classification: MERGE**

- Files: `Updated_Seatek_Analysis.R` (lines ~365), `.jules/palette.md`
- Change: Wraps `txtProgressBar` init and loop in `if (length(results) > 0)` guard
- Modifies a different section of R file than #88/#91 (line 365+ vs 131–260) — no conflict
- CI: CLEAN — all checks pass, CodeScene APPROVED
- Gate check: Safe UX/stability fix

### PR #90 — 🛡️ Sentinel: [MEDIUM] Ignore renv_restore.log
**Classification: MERGE**

- Files: `.gitignore` only
- Change: Adds `renv_restore.log` to `.gitignore`
- CI: CLEAN — all checks pass
- Gate check: Trivial gitignore entry. No security risk. Merge immediately

### PR #91 — ⚡ Bolt: Optimize R aggregation (newer, with tests)
**Classification: MERGE**

- Files: `Updated_Seatek_Analysis.R` (lines 131–260), `.jules/bolt.md`, `tests/testthat/test-process_all_data.R`
- Supersedes PR #88 — more complete fix with tests
- CI: CLEAN — all checks pass, CodeScene APPROVED
- Gate check: Performance optimization in R. No security surface. Safe

---

## Hydrograph_Versus_Seatek_Sensors_Project

### PR #79 — 🛡️ Sentinel: [CRITICAL] DoS fix (older)
**Classification: CLOSE-DUPE**

- Same fix as #81: removes global `Config()` instantiation from `data_validator.py`
- #79 uses `Config(base_dir=project_root)` and places fix slightly earlier in function
- #81 is newer, has CodeScene APPROVED review, CLEAN merge state, simpler patch
- **Action: Close as superseded by #81**

### PR #80 — ⚡ Bolt: Pandas masking optimization (comprehensive)
**Classification: MERGE**

- Files: `src/hydrograph_seatek_analysis/data/processor.py`, `app.py`, `validator.py`, `chart_generator.py`, `.jules/bolt.md`
- Changes: Caches `sensor_series`, pre-computes `isna` and `iszero` masks, replaces `.empty` with `len()`
- CI: CLEAN — all checks pass, CodeScene APPROVED
- **Conflicts with PR #82** (both modify same `sensor_mask` line in `processor.py`)
- PR #80 is more comprehensive (touches 4 more files); PR #82 is newer but narrower
- Decision: Merge #80, close #82 (the numpy `.values` optimization can be a follow-up)

### PR #81 — 🛡️ Sentinel: [HIGH] DoS fix (newer, cleaner)
**Classification: MERGE**

- Files: `data_validator.py`, `tests/test_data_validator_security.py`
- Removes global `config = Config()`, moves to local scope, uses `config.max_file_size_bytes`
- CI: CLEAN — all checks pass, CodeScene APPROVED
- No conflict with #80 (different files)

### PR #82 — ⚡ Bolt: Pandas numpy array masking (narrower, conflicts with #80)
**Classification: CLOSE-DUPE**

- Files: `src/hydrograph_seatek_analysis/data/processor.py`, `utils/processor.py`, `.jules/bolt.md`
- Conflicts with #80 at the `sensor_mask` line in `processor.py`
- PR #80 is more comprehensive and was created first (same day but earlier timestamp)
- **Action: Close as superseded by #80; note that `utils/processor.py` .values optimization can be a follow-up**

---

## Merge Execution Order

To minimize conflict risk, merge in this sequence:

**personal-config:**
1. #648 (CWE-78 fix — merge first)
2. Close #646 (superseded)
3. #647 (spinner — independent files, merge after #648)

**email-security-pipeline:**
4. #555 — HOLD; leave comment for Jules

**Seatek_Analysis:**
5. #87 (isolated file, merge anytime)
6. #90 (.gitignore, merge anytime)
7. Close #88 (superseded by #91)
8. #89 (R file lines 365+, merge before #91)
9. #91 (R file lines 131–260 + tests)

**Hydrograph:**
10. #81 (data_validator.py, merge first)
11. Close #79 (superseded)
12. Close #82 (superseded by #80)
13. #80 (processor.py, merge last after closing #82)
