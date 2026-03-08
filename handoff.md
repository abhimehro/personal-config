═════ ELIR ═════
PURPOSE: Extracted smaller helper functions out of the monolithic `monitor_controld` function in `maintenance/controld_monitor.sh`.
SECURITY: Maintained exact same process calls, checks, log targets, and return values.
FAILS IF: If any variables were incorrectly bound to parent shell scope (which none were, they were explicitly re-declared or simply returned error codes for orchestration).
VERIFY: Verify the original function flow matches the new flow and that log outputs are unchanged in normal circumstances.
MAINTAIN: New `verify_*` functions should return `0` (success) or `1` (failure) to feed into the `all_checks_passed` orchestration. Some don't fail the whole check (like upstream connectivity or mdns), these were preserved exactly.
