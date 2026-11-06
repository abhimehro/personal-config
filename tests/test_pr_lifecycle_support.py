"""Unit tests for shared value and format checks in scripts/pr_lifecycle_support.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pr_lifecycle_support import (  # noqa: E402
    KEY_RE,
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


class TestArtifactValidationError(unittest.TestCase):
    def test_inherits_from_value_error(self) -> None:
        self.assertTrue(issubclass(ArtifactValidationError, ValueError))
        err = ArtifactValidationError("fail-closed validation")
        self.assertIsInstance(err, ValueError)


class TestRequireMapping(unittest.TestCase):
    def test_valid_mapping(self) -> None:
        data = {"key": "val", "count": 1}
        result = require_mapping(data, "test_mapping")
        self.assertIs(result, data)
        self.assertEqual(result, {"key": "val", "count": 1})

    def test_empty_mapping(self) -> None:
        data: dict[str, str] = {}
        result = require_mapping(data, "empty_dict")
        self.assertIs(result, data)

    def test_non_mapping_types_raise_artifact_validation_error(self) -> None:
        invalid_cases = [
            ("string", "expected mapping"),
            ([1, 2, 3], "expected mapping"),
            (None, "expected mapping"),
            (123, "expected mapping"),
            (True, "expected mapping"),
            ({1, 2, 3}, "expected mapping"),
            ((1, 2), "expected mapping"),
        ]
        for val, err_msg in invalid_cases:
            with self.subTest(val=val):
                with self.assertRaises(ArtifactValidationError) as ctx:
                    require_mapping(val, "item_label")
                self.assertIn("item_label: expected mapping", str(ctx.exception))


class TestRequireList(unittest.TestCase):
    def test_valid_list(self) -> None:
        data = ["a", "b", "c"]
        result = require_list(data, "test_list")
        self.assertIs(result, data)
        self.assertEqual(result, ["a", "b", "c"])

    def test_empty_list(self) -> None:
        data: list[str] = []
        result = require_list(data, "empty_list")
        self.assertIs(result, data)

    def test_non_list_types_raise_artifact_validation_error(self) -> None:
        invalid_cases = [
            ("string", "expected list"),
            ({"a": 1}, "expected list"),
            (None, "expected list"),
            (123, "expected list"),
            (True, "expected list"),
            ({1, 2, 3}, "expected list"),
            ((1, 2), "expected list"),
        ]
        for val, err_msg in invalid_cases:
            with self.subTest(val=val):
                with self.assertRaises(ArtifactValidationError) as ctx:
                    require_list(val, "list_label")
                self.assertIn("list_label: expected list", str(ctx.exception))


class TestRequireFields(unittest.TestCase):
    def test_valid_exact_fields(self) -> None:
        data = {"a": 1, "b": 2}
        allowed = {"a", "b"}
        required = {"a", "b"}
        require_fields(data, allowed, required, "fields_test")

    def test_valid_superset_allowed(self) -> None:
        data = {"a": 1}
        allowed = {"a", "b", "c"}
        required = {"a"}
        require_fields(data, allowed, required, "fields_test")

    def test_unknown_fields_raise_value_error(self) -> None:
        data = {"a": 1, "extra": 2, "unsupported": 3}
        allowed = {"a"}
        required = {"a"}
        with self.assertRaises(ValueError) as ctx:
            require_fields(data, allowed, required, "fields_label")
        self.assertIn("fields_label: unsupported fields: ['extra', 'unsupported']", str(ctx.exception))

    def test_missing_required_fields_raise_value_error(self) -> None:
        data = {"a": 1}
        allowed = {"a", "b", "c"}
        required = {"a", "b", "c"}
        with self.assertRaises(ValueError) as ctx:
            require_fields(data, allowed, required, "fields_label")
        self.assertIn("fields_label: missing required fields: ['b', 'c']", str(ctx.exception))

    def test_unknown_field_takes_precedence_over_missing_fields(self) -> None:
        # When both unknown and missing fields occur, unknown is checked first
        data = {"unknown_key": 1}
        allowed = {"required_key"}
        required = {"required_key"}
        with self.assertRaises(ValueError) as ctx:
            require_fields(data, allowed, required, "fields_label")
        self.assertIn("fields_label: unsupported fields: ['unknown_key']", str(ctx.exception))


class TestRequireUtc(unittest.TestCase):
    def test_valid_utc_timestamps(self) -> None:
        valid_timestamps = [
            "2026-08-20T14:30:00Z",
            "2026-01-01T00:00:00.000Z",
            "2026-12-31T23:59:59.123456Z",
        ]
        for ts in valid_timestamps:
            with self.subTest(ts=ts):
                require_utc(ts, "ts_label")

    def test_invalid_utc_timestamps_raise_value_error(self) -> None:
        invalid_cases = [
            None,
            123456789,
            "2026-08-20 14:30:00",
            "2026-08-20T14:30:00",
            "2026-08-20T14:30:00+00:00",
            "2026-08-20T14:30:00-05:00",
            "2026/08/20T14:30:00Z",
            "invalid-date",
            "",
        ]
        for val in invalid_cases:
            with self.subTest(val=val):
                with self.assertRaises(ValueError) as ctx:
                    require_utc(val, "ts_label")
                self.assertIn("ts_label: expected RFC 3339 UTC timestamp", str(ctx.exception))


class TestRequireHttpsUrl(unittest.TestCase):
    def test_valid_https_urls(self) -> None:
        valid_urls = [
            "https://github.com/abhimehro/personal-config",
            "https://example.com/path?query=val#fragment",
            "https://api.github.com/repos/owner/repo/pulls/1",
        ]
        for url in valid_urls:
            with self.subTest(url=url):
                require_https_url(url, "url_label")

    def test_invalid_urls_raise_value_error(self) -> None:
        invalid_cases = [
            None,
            123,
            "http://github.com/abhimehro/personal-config",
            "ftp://files.example.com",
            "https://",
            "https:///path/only",
            "https:// space-in-host.com",
            "not-a-url",
            "",
        ]
        for val in invalid_cases:
            with self.subTest(val=val):
                with self.assertRaises(ValueError) as ctx:
                    require_https_url(val, "url_label")
                self.assertIn("url_label: expected complete https URL", str(ctx.exception))


class TestRequireHttpsUrls(unittest.TestCase):
    def test_valid_https_urls_list(self) -> None:
        urls = [
            "https://github.com/abhimehro/personal-config/pull/1",
            "https://github.com/abhimehro/personal-config/pull/2",
        ]
        require_https_urls(urls, "urls_list")

    def test_empty_list_is_valid(self) -> None:
        require_https_urls([], "empty_urls")

    def test_non_list_raises_artifact_validation_error(self) -> None:
        with self.assertRaises(ArtifactValidationError) as ctx:
            require_https_urls("https://github.com", "urls_list")
        self.assertIn("urls_list: expected list", str(ctx.exception))

    def test_invalid_url_in_list_raises_value_error_with_indexed_label(self) -> None:
        urls = [
            "https://github.com/valid",
            "http://insecure.example.com",
        ]
        with self.assertRaises(ValueError) as ctx:
            require_https_urls(urls, "evidence_urls")
        self.assertIn("evidence_urls[1]: expected complete https URL", str(ctx.exception))


class TestRegexPatterns(unittest.TestCase):
    def test_key_re(self) -> None:
        valid_keys = [
            "abhimehro/personal-config#1@0123456789abcdef0123456789abcdef01234567",
            "owner-name/repo.name#999@abcdef0123456789abcdef0123456789abcdef01",
        ]
        for key in valid_keys:
            with self.subTest(key=key):
                self.assertIsNotNone(KEY_RE.fullmatch(key))

        invalid_keys = [
            "owner/repo#0@0123456789abcdef0123456789abcdef01234567",  # PR number 0
            "owner/repo#1@0123456789abcdef",  # Short SHA
            "owner/repo#1",  # Missing SHA
            "owner#1@0123456789abcdef0123456789abcdef01234567",  # Missing repo
            "owner/repo#1@0123456789ABCDEF0123456789ABCDEF01234567",  # Uppercase SHA
        ]
        for key in invalid_keys:
            with self.subTest(key=key):
                self.assertIsNone(KEY_RE.fullmatch(key))

    def test_sha_re(self) -> None:
        valid_sha = "0123456789abcdef0123456789abcdef01234567"
        self.assertIsNotNone(SHA_RE.fullmatch(valid_sha))

        invalid_shas = [
            "0123456789abcdef0123456789abcdef0123456",  # 39 chars
            "0123456789abcdef0123456789abcdef012345678",  # 41 chars
            "0123456789ABCDEF0123456789ABCDEF01234567",  # Uppercase
            "g" * 40,  # Non-hex character
        ]
        for sha in invalid_shas:
            with self.subTest(sha=sha):
                self.assertIsNone(SHA_RE.fullmatch(sha))

    def test_utc_re(self) -> None:
        self.assertIsNotNone(UTC_RE.fullmatch("2026-08-20T12:00:00Z"))
        self.assertIsNotNone(UTC_RE.fullmatch("2026-08-20T12:00:00.123456Z"))
        self.assertIsNone(UTC_RE.fullmatch("2026-08-20 12:00:00Z"))
        self.assertIsNone(UTC_RE.fullmatch("2026-08-20T12:00:00+00:00"))

    def test_url_re(self) -> None:
        self.assertIsNotNone(URL_RE.fullmatch("https://example.com"))
        self.assertIsNotNone(URL_RE.fullmatch("https://example.com/path?a=1#frag"))
        self.assertIsNone(URL_RE.fullmatch("http://example.com"))
        self.assertIsNone(URL_RE.fullmatch("https://example .com"))


if __name__ == "__main__":
    unittest.main()
