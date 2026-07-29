========== ELIR ==========
PURPOSE: Optimized the `extract_status_markers` function in `.github/scripts/repository_automation_tasks.py` by extracting the static regular expression and compiling it at the module level using `re.compile(..., re.S)`. This avoids redundant regex compilation on each function call.
SECURITY: No direct security implications; strictly a performance optimization for text parsing. Assumes `issue_body` is a string (checked by type hinting).
FAILS IF: The regex syntax was somehow altered, but it was verified to be identical to the original inline regex.
VERIFY: Check that the compiled regex correctly extracts status markers from test data (verified via `make test-all`).
MAINTAIN: If the marker format changes (e.g., from `<!-- repository-automation:task-status\n(.*?)\n-->`), update `_STATUS_MARKER_RE` at the module level.
