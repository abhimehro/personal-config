[x] Reproduce the missing test coverage locally and understand what commands controld-manager exposes
[x] Identify dependencies to mock (sudo, launchctl, networksetup, dscacheutil, killall, pkill, pgrep, ping, ctrld)
[x] Write targeted tests in tests/test_controld_manager.sh mapping to commands start, stop, status, switch-profile, emergency
[x] Hook tests up to run_all_tests.sh (done natively)
[x] Run the full suite to verify existing CI outputs aren't broken
