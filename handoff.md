# 🧪 Testing Improvement Task

## 🎯 What

Added missing test coverage for `format_lists` in `generate_report.py`. The
`format_lists` function contains a generator expression that expects a tuple
with three elements (`repo, pr, title`). If the data passed to it is malformed
(e.g., missing the title), it crashes with a `ValueError` during tuple
unpacking. This scenario wasn't previously tested.

## 📊 Coverage

Added `test_format_lists_missing_fields` to explicitly trigger and assert the
`ValueError` when `merged_data` is supplied a malformed tuple with only two
elements.

## ✨ Result

Improved test resilience. The test suite now guards against unpacking
regressions in the core PR reporting function `format_lists`.

========== ELIR ========== PURPOSE: Add edge-case coverage to ensure
`format_lists` raises `ValueError` cleanly on malformed input. SECURITY: N/A -
pure testing robustness. FAILS IF: The data parsing upstream fails to output
triplets (`repo`, `pr`, `title`). VERIFY: Confirm
`test_format_lists_missing_fields` explicitly tests the ValueError catch.
MAINTAIN: Keep this updated if `format_lists` changes its expected tuple
structure.
