- [x] Analyze `generate_report.py:40` for missing error test in `format_lists`.
- [x] Write `test_format_lists_missing_fields` to cover the exact `ValueError`
      unpacking scenario.
- [x] Inject the new test correctly into `tests/test_generate_report.py`.
- [x] Run `make test-all` and ensure no regressions.
- [x] Analyze `gh_token_env.py` for missing OSError test in `_read_env_file`.
- [x] Write `test_read_env_file_oserror` to cover `FileNotFoundError` and `PermissionError` paths.
- [x] Run full tests to ensure no regressions.
- [x] Replace `# Try to fix permissions` with `# Automatically correct permissions` in `scripts/verify_all_configs.sh`.
