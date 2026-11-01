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


class TestPrLifecycleSupport(unittest.TestCase):
    def test_root_path(self) -> None:
        self.assertEqual(SUPPORT_ROOT, ROOT)

    def test_artifact_validation_error_hierarchy(self) -> None:
        self.assertTrue(issubclass(ArtifactValidationError, ValueError))
        err = ArtifactValidationError("fail-closed error")
        self.assertIsInstance(err, ValueError)
        self.assertEqual(str(err), "fail-closed error")

    def test_require_mapping_valid(self) -> None:
        cases = [
            {},
            {"key": "value"},
            {"a": 1, "b": [1, 2]},
        ]
        for val in cases:
            with self.subTest(val=val):
                res = require_mapping(val, "metadata")
                self.assertIs(res, val)

    def test_require_mapping_invalid(self) -> None:
        invalid_values = [
            None,
            [],
            [1, 2],
            "string",
            123,
            True,
            (1, 2),
            {1, 2},
        ]
        for val in invalid_values:
            with self.subTest(val=val):
                with self.assertRaises(ArtifactValidationError) as ctx:
                    require_mapping(val, "item.config")
                self.assertIn("item.config: expected mapping", str(ctx.exception))

    def test_require_list_valid(self) -> None:
        cases = [
            [],
            [1, 2, 3],
            ["a", "b"],
            [{"k": "v"}],
        ]
        for val in cases:
            with self.subTest(val=val):
                res = require_list(val, "tags")
                self.assertIs(res, val)

    def test_require_list_invalid(self) -> None:
        invalid_values = [
            None,
            {},
            {"a": 1},
            "string",
            123,
            True,
            (1, 2),
            {1, 2},
        ]
        for val in invalid_values:
            with self.subTest(val=val):
                with self.assertRaises(ArtifactValidationError) as ctx:
                    require_list(val, "item.steps")
                self.assertIn("item.steps: expected list", str(ctx.exception))

    def test_require_fields_valid(self) -> None:
        allowed = {"a", "b", "c"}
        required = {"a", "b"}

        # Exact match
        require_fields({"a": 1, "b": 2}, allowed, required, "field_test")
        # Allowed superset
        require_fields({"a": 1, "b": 2, "c": 3}, allowed, required, "field_test")

    def test_require_fields_missing(self) -> None:
        allowed = {"a", "b", "c"}
        required = {"a", "b", "c"}

        with self.assertRaises(ValueError) as ctx:
            require_fields({"a": 1}, allowed, required, "test_item")
        self.assertEqual(
            str(ctx.exception),
            "test_item: missing required fields: ['b', 'c']",
        )

    def test_require_fields_unsupported(self) -> None:
        allowed = {"a", "b"}
        required = {"a"}

        with self.assertRaises(ValueError) as ctx:
            require_fields({"a": 1, "extra1": 2, "extra2": 3}, allowed, required, "test_item")
        self.assertEqual(
            str(ctx.exception),
            "test_item: unsupported fields: ['extra1', 'extra2']",
        )

    def test_require_fields_unknown_takes_precedence_over_missing(self) -> None:
        allowed = {"a", "b"}
        required = {"a", "b"}

        # Missing 'b', but contains 'extra'
        with self.assertRaises(ValueError) as ctx:
            require_fields({"a": 1, "extra": 2}, allowed, required, "test_item")
        self.assertEqual(
            str(ctx.exception),
            "test_item: unsupported fields: ['extra']",
        )

    def test_require_utc_valid(self) -> None:
        valid_timestamps = [
            "2026-08-20T12:00:00Z",
            "2026-01-01T00:00:00.123Z",
            "2026-12-31T23:59:59.999999Z",
        ]
        for ts in valid_timestamps:
            with self.subTest(ts=ts):
                require_utc(ts, "created_at")

    def test_require_utc_invalid(self) -> None:
        invalid_timestamps = [
            None,
            1234567890,
            "",
            "2026-08-20",
            "2026-08-20T12:00:00",
            "2026-08-20T12:00:00+00:00",
            "2026-08-20T12:00:00-05:00",
            "2026-08-20 12:00:00Z",
            "invalid-date",
            "2026-08-20T12:00:00Z extra",
        ]
        for ts in invalid_timestamps:
            with self.subTest(ts=ts):
                with self.assertRaises(ValueError) as ctx:
                    require_utc(ts, "updated_at")
                self.assertEqual(str(ctx.exception), "updated_at: expected RFC 3339 UTC timestamp")

    def test_require_https_url_valid(self) -> None:
        valid_urls = [
            "https://github.com/abhimehro/personal-config",
            "https://github.com/owner/repo/pull/123",
            "https://api.github.com/repos/owner/repo?param=value#anchor",
            "https://example.com:8443/test",
        ]
        for url in valid_urls:
            with self.subTest(url=url):
                require_https_url(url, "html_url")

    def test_require_https_url_invalid(self) -> None:
        invalid_urls = [
            None,
            123,
            "",
            "http://github.com",
            "ftp://example.com",
            "https://",
            "https:// example.com",
            "https://example.com with spaces",
            "not a url",
            "https:///path-without-host",
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError) as ctx:
                    require_https_url(url, "evidence_url")
                self.assertEqual(str(ctx.exception), "evidence_url: expected complete https URL")

    def test_require_https_urls_valid(self) -> None:
        require_https_urls([], "urls")
        require_https_urls(
            [
                "https://github.com/a/b",
                "https://example.org/path",
            ],
            "urls",
        )

    def test_require_https_urls_invalid_container(self) -> None:
        with self.assertRaises(ArtifactValidationError) as ctx:
            require_https_urls("https://github.com/a/b", "urls")
        self.assertEqual(str(ctx.exception), "urls: expected list")

    def test_require_https_urls_invalid_element(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            require_https_urls(
                ["https://github.com/a/b", "http://insecure.org"],
                "sources",
            )
        self.assertEqual(str(ctx.exception), "sources[1]: expected complete https URL")

    def test_regex_key_re(self) -> None:
        valid_keys = [
            "abhimehro/personal-config#123@0123456789abcdef0123456789abcdef01234567",
            "owner.sub-name/repo_name#1@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        ]
        for k in valid_keys:
            with self.subTest(k=k):
                self.assertIsNotNone(KEY_RE.fullmatch(k))

        invalid_keys = [
            "abhimehro/personal-config#0@0123456789abcdef0123456789abcdef01234567",
            "abhimehro/personal-config#123@0123456789abcdef",
            "abhimehro/personal-config#123",
            "owner/repo#123@0123456789ABCDEF0123456789ABCDEF01234567",
            "owner/repo#123@g123456789abcdef0123456789abcdef01234567",
        ]
        for k in invalid_keys:
            with self.subTest(k=k):
                self.assertIsNone(KEY_RE.fullmatch(k))

    def test_regex_sha_re(self) -> None:
        self.assertIsNotNone(SHA_RE.fullmatch("0123456789abcdef0123456789abcdef01234567"))
        self.assertIsNone(SHA_RE.fullmatch("0123456789ABCDEF0123456789ABCDEF01234567"))
        self.assertIsNone(SHA_RE.fullmatch("123456"))
        self.assertIsNone(SHA_RE.fullmatch("0123456789abcdef0123456789abcdef012345678"))
        self.assertIsNone(SHA_RE.fullmatch("g123456789abcdef0123456789abcdef01234567"))

    def test_regex_utc_re(self) -> None:
        self.assertIsNotNone(UTC_RE.fullmatch("2026-08-20T12:00:00Z"))
        self.assertIsNotNone(UTC_RE.fullmatch("2026-08-20T12:00:00.123456Z"))
        self.assertIsNone(UTC_RE.fullmatch("2026-08-20T12:00:00"))
        self.assertIsNone(UTC_RE.fullmatch("2026-08-20 12:00:00Z"))

    def test_regex_url_re(self) -> None:
        self.assertIsNotNone(URL_RE.fullmatch("https://example.com/test"))
        self.assertIsNone(URL_RE.fullmatch("http://example.com"))
        self.assertIsNone(URL_RE.fullmatch("https://example.com with space"))


if __name__ == "__main__":
    unittest.main()
