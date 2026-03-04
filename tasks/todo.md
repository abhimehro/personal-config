# Task: Extract DNS utility functions from controld-manager

## Approach
- Created `scripts/lib/dns-utils.sh` (or updated existing) and moved `backup_network_settings`, `restore_network_settings`, and `test_dns_resolution`.
- Created `scripts/lib/controld-profile.sh` for profile logic (`get_profile_id`, `generate_profile_config`, `test_profile_connection`).
- Created `scripts/lib/controld-service.sh` for lifecycle management (`setup_directories`, `safe_stop`, `restart_with_config`, `emergency_recovery`, `show_status`).
- `controld-manager` reduced from 759 lines to 244 lines.
- Wrote tests for all 4 shell scripts (`test_dns_utils.sh`, `test_controld_profile.sh`, `test_controld_service.sh`, `test_controld_manager.sh`) which mirror their respective source modules.
- Updated `test_controld_validation.sh` to work with the updated guard in `controld-manager`.

## Completion
- All task steps completed. Code is structured cleanly and tests pass.

[x] Reproduce the missing test coverage locally and understand what commands control-manager exposes
[x] Identify dependencies to mock (sudo, launchctl, networksetup, dscacheutil, killall, pkill, pgrep, ping, ctrld)
[x] Write targeted tests in tests/test_controld_manager.sh mapping to commands start, stop, status, switch-profile, emergency
[x] Hook tests up to run_all_tests.sh (done natively)
[x] Run the full suite to verify existing CI outputs aren't broken
