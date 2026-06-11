========== ELIR ==========
PURPOSE: Added test coverage for `_group_prs_by_files` in `detect_duplicates.py` using `unittest.mock.patch` to mock GitHub API calls inside the ThreadPoolExecutor map.
SECURITY: No security implications; test-only code. Mocking prevents accidental live API execution or rate-limiting during CI runs.
FAILS IF: The implementation of `_group_prs_by_files` or the mocked behavior of `fetch_pr_info` significantly changes.
VERIFY: Run `python3 -m unittest tests.test_detect_duplicates` and confirm 8 tests pass without errors.
MAINTAIN: If `fetch_pr_info` starts returning a different tuple structure or throwing exceptions instead of returning None on failure, update the side_effects/return_values in these tests.
