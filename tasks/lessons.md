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
