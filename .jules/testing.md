## 2026-06-29 - Improve Testing using Mock
**Learning:** For file I/O operations and third party calls like `extract_domains_from_file`, tests should mock the Path objects or underlying calls to isolate the business logic and ensure deterministic tests without real disk writes.
**Action:** Replace `unittest.TestCase` relying on actual file dumps with mocked `Path` structures using `@patch` and `MagicMock`.
