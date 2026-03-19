# Lessons Learned — Control D Pipeline Fix (2026-03-15)

## Lesson 1: Hardcoded paths break test isolation
**Pattern:** Scripts that hardcode `/etc/controld/...` fail in non-root test environments.
**Rule:** Always use `${CONTROLD_DIR:-/etc/controld}` for any path under the controld config directory. Apply this consistently across all files that reference the directory — not just the main script.

## Lesson 2: Generated TOML ≠ Dashboard Attribution
**Pattern:** `ctrld` generates a `ctrld.toml` on start regardless of how it was invoked, but the `--cd <profile_id>` flag is what provides dashboard-level attribution.
**Rule:** Don't confuse the auto-generated local config with proof of dashboard connectivity. The native `--cd` flag is the correct mechanism for profile attribution.

## Lesson 3: Test mocks must cover new functions
**Pattern:** Introducing `restart_with_native_profile` broke `test_controld_validation.sh` because only `restart_with_config` was mocked.
**Rule:** When adding a new function to the call path, immediately update all test files that mock functions in that path.

# Lessons Learned — Automated PR Review Agent
**Run date:** 2026-03-19  
**Workflow:** backlog-cleanup, review-and-merge mode

---

## What Worked Well

### 1. Bot-authored PR detection via branch naming
All 13 PRs in scope were authored by `abhimehro` on GitHub but clearly bot-generated. The detection pattern was reliable: Jules task IDs in branch names (e.g., `sentinel-fix-cwe-78-eval-1490423628044885716`), emoji prefixes in titles (`🛡️ Sentinel:`, `⚡ Bolt:`, `🎨 Palette:`), and explicit footer text `PR created automatically by Jules for task ...`. This pattern should be formalized in the agent's bot-detection heuristic.

### 2. Duplicate detection across repos
The most important discovery in this run: 4 of 13 PRs (31%) were duplicates fixing the same issue. Jules had generated multiple PRs for the same vulnerability/task without awareness of prior open PRs. The duplicate pairs:
- personal-config #648 vs #646 (CWE-78 eval, same 3 files, 1 day apart)
- Hydrograph #81 vs #79 (DoS Config bypass, same file, 1 day apart)
- Seatek #91 vs #88 (data.table aggregation, same R lines, 1 day apart)
- Hydrograph #82 vs #80 (pandas masking, overlapping lines in processor.py, same day)

**Root cause:** Jules generates new PRs on each task invocation without checking for existing open PRs addressing the same code. The bot starts fresh.

**Prevention pattern:** Before creating a PR, the orchestration layer should query `gh pr list --repo ... --state open` and check for branch name overlap or same-file diffs.

### 3. Codacy CANCELLED ≠ CI failure
In `personal-config`, Codacy Security Scan consistently shows as CANCELLED across all PRs. This is a known transient issue with Codacy's GitHub integration, not caused by the PRs. The policy "never merge failing CI unless clearly unrelated" applies here — CANCELLED is not FAILED, and the Codacy scan not running is unrelated to the code changes. The other 11 checks all pass. This distinction saved 2 merges from being incorrectly blocked.

### 4. CodeScene failure IS related
In `email-security-pipeline` #555, CodeScene flagged genuine code quality regressions in the PR's changed files — complex methods in `ui.py`, `main.py`, `setup_wizard.py`. Unlike the CANCELLED Codacy check above, this is a real failure directly caused by the PR's changes. Correctly classified as HOLD.

---

## What Needs Improvement

### 5. Authentication scope gap
**Problem:** The cursor agent's GitHub App installation token has `contents: write` (git push) but not `pull_requests: write` or `issues: write`. This blocked all API-level actions: merging PRs, closing PRs, and leaving comments. The agent could analyze but not act.

**Fix:** The cursor agent's GitHub App must have the following permissions granted for each target repo:
- `pull_requests: write` — to merge and close PRs
- `issues: write` — to post comments (PR comments use the issues API)

Until then, a PAT for `abhimehro` should be added as a Cursor Cloud Agent secret (`GITHUB_PAT`) and used via `GH_TOKEN=<PAT> gh pr merge ...`.

### 6. Conflict ordering is non-trivial
Multiple PRs touching the same file in the same repo require a careful merge order. In this run:
- Seatek #88 and #91 both modify the same lines of `Updated_Seatek_Analysis.R`
- Hydrograph #80 and #82 both modify the `sensor_mask` line of `processor.py`
- Seatek #89 is safe to merge alongside others (different R file section)

**Rule established:** When multiple bot PRs touch the same file:
1. Close the older PR first if it's a true duplicate (identical intent, same lines)
2. If the PRs are complementary but conflicting, pick the more comprehensive one and note the missed optimization for a follow-up

### 7. Jules doesn't observe other open PRs
Jules operates in isolation per task. When the same or similar issues get filed multiple times, Jules creates multiple independent PRs. An orchestration improvement: after Jules creates a PR, the system should automatically run a similarity check against open PRs in the same repo and flag potential duplicates to the user before proceeding.

### 8. utils/processor.py optimization missed
Hydrograph PR #82 touched `utils/processor.py` (extracting numpy `.values` arrays) which PR #80 did NOT touch. By closing #82 as superseded by #80, the numpy optimization in `utils/processor.py` is lost. A follow-up PR should be filed to apply this specific change. **Action item for Jules:** Create a targeted PR adding `.values` extraction to `utils/processor.py` lines 174–192.

---

## Policy Calibration Notes

- **Codacy CANCELLED policy:** Treat CANCELLED (not FAILED) as unrelated and allow merge when all other required checks pass.
- **CodeScene advisory gates:** Treat CodeScene FAILURE (not just COMMENTED) as a blocking failure when it flags the PR's own files.
- **"UNSTABLE" merge state:** Investigate before merging. In personal-config, UNSTABLE was caused by CANCELLED (non-blocking). In email-security-pipeline, UNSTABLE was caused by FAILURE (blocking).
- **Jules bot security note:** Jules commits are `co-authored-by: abhimehro` — this is expected and does not indicate human review or approval of the changes.
- **Merge order matters:** When PRs from the same Jules session touch the same file, always merge the newer/more complete one and close the older one before merging.

---

## Metrics for This Run

| Metric | Count |
|--------|-------|
| Repos processed | 5 (1 had 0 PRs) |
| Total PRs inventoried | 13 |
| PRs ready to merge | 8 |
| PRs to close as duplicate | 4 |
| PRs held (CI failure) | 1 |
| PRs escalated | 0 |
| PRs merged (actual) | 0 — auth blocked |
| PRs closed (actual) | 0 — auth blocked |
| Comments left | 0 — auth blocked |
| Stale PRs (>30 days) | 0 |
