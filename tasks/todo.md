# Task: Fix Control D Profile Attribution - 2026-03-15

Route: T1+S+H

## Trust Boundaries

- We are moving from local TOML profile generation to the native Control D resolver-ID path via `ctrld`'s internal lookup scheme.
- The `ctrld` executable must be trusted to pull the profile configurations privately and verify upstream authenticity.
- We must ensure that the profile ID inputs correspond precisely to the user's registered Control D device setups.

## Plan

- [x] Refactor `scripts/lib/controld-service.sh` to add `restart_with_native_profile` and use an `/etc/controld/active_profile` state file.
- [x] Implement resilient Windscribe CLI detection in `scripts/windscribe-connect.sh`
- [x] Interactively extract `mole` features from `stash@{0}`
- [x] Extract `rename-media.sh` fixes from `stash@{0}`
- [x] Drop `stash@{0}` to purposefully discard the vulnerable modifications (to preserve CWE-78 and CWE-377 fixes)
- [ ] Verify functionality and update walkthrough
