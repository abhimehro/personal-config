# Task: Fix Control D Profile Attribution - 2026-03-15

Route: T1+S+H

## Trust Boundaries
- We are moving from local TOML profile generation to the native Control D resolver-ID path via `ctrld`'s internal lookup scheme.
- The `ctrld` executable must be trusted to pull the profile configurations privately and verify upstream authenticity.
- We must ensure that the profile ID inputs correspond precisely to the user's registered Control D device setups.

## Plan
- [x] Refactor `scripts/lib/controld-service.sh` to add `restart_with_native_profile` and use an `/etc/controld/active_profile` state file.
- [x] Refactor `controld-system/scripts/controld-manager` to bypass `generate_profile_config` and invoke the native process.
- [x] Update status commands to read from the state file (`active_profile`).
- [x] Make `CONTROLD_DIR` overridable via env var in `controld-manager`, `controld-service.sh`, and `network-core.sh`.
- [x] Perform a live test of `sudo controld-manager switch privacy doh`.
- [x] Fix test regressions in `test_controld_manager.sh`, `test_controld_validation.sh`, `test_network_mode_manager.sh`, and `test_controld_service.sh`.
- [x] Run automated tests — all controld and network tests pass, no new regressions.
- [ ] Document lessons and present an ELIR summary.
