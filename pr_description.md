🎯 **What:** The PR categorization logic in `categorize_ready.py` was previously an inline loop, making it difficult to verify all code paths. Missing parsing tests for this file have now been addressed.
📊 **Coverage:** The logic has been extracted into a testable `get_category_from_title` function, with tests covering the scenarios for SECURITY, DEPENDENCY, CI/INFRA, and the default PERFORMANCE/REFACTOR/UI/FEATURE categories.
✨ **Result:** Improved test coverage, ensuring PRs are correctly categorized and catching regressions during modifications.
