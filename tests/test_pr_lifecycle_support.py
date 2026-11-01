"""Unit tests for scripts/pr_lifecycle_support.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pr_lifecycle_support import (
    KEY_RE,
    ROOT as SUPPORT_ROOT,
    SHA_RE,
    URL_RE,
    UTC_RE,
    ArtifactValidationError,
    require_fields,
    require_https_url,
    require_https_urls,
    require_list,
    require_mapping,
    require_utc,
)

INVALID_INPUT_TYPES = (
    None,
    [],
    [1, 2],
    "string",
    123,
    True,
    (1, 2),
    {1, 2},
)


class TestPrLifecycleSupport(unittest.TestCase):
    def test_root_path_and_error_hierarchy(self) -> None:
        self.assertEqual(SUPPORT_ROOT, ROOT)
        self.assertTrue(issubclass(ArtifactValidationError, ValueError))
        err = ArtifactValidationError("fail-closed error")
        self.assertIsInstance(err, ValueError)
        self.assertEqual(str(err), "fail-closed error")

    def test_require_mapping(self) -> None:
        valid_payloads = ({}, {"key": "value"}, {"nested": [1, 2]})
        for mapping in valid_payloads:
            self.assertIs(require_mapping(mapping, "item"), mapping)

        for invalid in INVALID_INPUT_TYPES:
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ArtifactValidationError, "item: expected mapping"):
                    require_mapping(invalid, "item")

    def test_require_list(self) -> None:
        valid_sequences = ([], [1, 2, 3], [{"item": "val"}])
        for seq in valid_sequences:
            self.assertIs(require_list(seq, "steps"), seq)

        invalid_sequences = (None, {}, {"a": 1}, "string", 123, True, (1, 2), {1, 2})
        for invalid in invalid_sequences:
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ArtifactValidationError, "steps: expected list"):
                    require_list(invalid, "steps")

    def test_require_fields(self) -> None:
        allowed = {"a", "b", "c"}
        required = {"a", "b"}

        # Exact and allowed superset passes
        require_fields({"a": 1, "b": 2}, allowed, required, "test_item")
        require_fields({"a": 1, "b": 2, "c": 3}, allowed, required, "test_item")

        # Missing required
        with self.assertRaisesRegex(ValueError, r"test_item: missing required fields: \['b', 'c'\]"):
            require_fields({"a": 1}, allowed, {"a", "b", "c"}, "test_item")

        # Unsupported keys
        with self.assertRaisesRegex(ValueError, r"test_item: unsupported fields: \['x', 'y'\]"):
            require_fields({"a": 1, "x": 2, "y": 3}, allowed, required, "test_item")

        # Unknown takes precedence over missing
        with self.assertRaisesRegex(ValueError, r"test_item: unsupported fields: \['extra'\]"):
            require_fields({"a": 1, "extra": 2}, allowed, required, "test_item")

    def test_require_utc(self) -> None:
        valid_ts = ("2026-08-20T12:00:00Z", "2026-01-01T00:00:00.123Z")
        for ts in valid_ts:
            require_utc(ts, "created_at")

        invalid_ts = (None, 123, "", "2026-08-20", "2026-08-20T12:00:00+00:00", "2026-08-20 12:00:00Z")
        for ts in invalid_ts:
            with self.subTest(ts=ts):
                with self.assertRaisesRegex(ValueError, "updated_at: expected RFC 3339 UTC timestamp"):
                    require_utc(ts, "updated_at")

    def test_require_https_url(self) -> None:
        valid_urls = (
            "https://github.com/abhimehro/personal-config",
            "https://api.github.com/repos/owner/repo?param=value#anchor",
            "https://example.com:8443/test",
        )
        for url in valid_urls:
            require_https_url(url, "html_url")

        invalid_urls = (None, 123, "", "http://insecure.com", "https://", "https:///path", "https://site com")
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "evidence_url: expected complete https URL"):
                    require_https_url(url, "evidence_url")

    def test_require_https_urls(self) -> None:
        require_https_urls([], "urls")
        require_https_urls(["https://example.org/1", "https://example.org/2"], "urls")

        with self.assertRaisesRegex(ArtifactValidationError, "urls: expected list"):
            require_https_urls("https://example.org", "urls")

        with self.assertRaisesRegex(ValueError, r"sources\[1\]: expected complete https URL"):
            require_https_urls(["https://example.org", "http://bad.org"], "sources")

    def test_regex_patterns(self) -> None:
        # KEY_RE
        valid_key = "owner/repo#123@0123456789abcdef0123456789abcdef01234567"
        self.assertIsNotNone(KEY_RE.fullmatch(valid_key))
        self.assertIsNone(KEY_RE.fullmatch("owner/repo#0@0123456789abcdef0123456789abcdef01234567"))
        self.assertIsNone(KEY_RE.fullmatch("owner/repo#123@short"))

        # SHA_RE
        valid_sha = "0123456789abcdef0123456789abcdef01234567"
        self.assertIsNotNone(SHA_RE.fullmatch(valid_sha))
        self.assertIsNone(SHA_RE.fullmatch("0123456789ABCDEF0123456789ABCDEF01234567"))
        self.assertIsNone(SHA_RE.fullmatch("12345"))

        # UTC_RE
        self.assertIsNotNone(UTC_RE.fullmatch("2026-08-20T12:00:00Z"))
        self.assertIsNotNone(UTC_RE.fullmatch("2026-08-20T12:00:00.123456Z"))
        self.assertIsNone(UTC_RE.fullmatch("2026-08-20T12:00:00"))

        # URL_RE
        self.assertIsNotNone(URL_RE.fullmatch("https://example.com/test"))
        self.assertIsNone(URL_RE.fullmatch("http://example.com"))


if __name__ == "__main__":
    unittest.main()
