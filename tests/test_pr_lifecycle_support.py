"""Unit tests for scripts/pr_lifecycle_support.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, Callable

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


class BaseValidatorTest(unittest.TestCase):
    """Shared assertion helpers to avoid repetitive test structures."""

    def assert_rejects(
        self,
        validator: Callable[[Any, str], Any],
        values: tuple[Any, ...],
        expected_exc: type[Exception],
        pattern: str,
        label: str = "field",
    ) -> None:
        for val in values:
            with self.subTest(val=val):
                with self.assertRaisesRegex(expected_exc, pattern):
                    validator(val, label)


class TestPrLifecycleSupportMappingAndList(BaseValidatorTest):
    """Test require_mapping and require_list validators."""

    def test_require_mapping_valid(self) -> None:
        sample_dict = {"a": 1, "nested": {"key": "val"}}
        self.assertEqual(require_mapping(sample_dict, "label"), sample_dict)
        self.assertEqual(require_mapping({}, "label"), {})

    def test_require_mapping_invalid(self) -> None:
        invalid_types = (None, [], [("a", 1)], "not_a_dict", 123, True, False, {1, 2})
        self.assert_rejects(
            require_mapping,
            invalid_types,
            ArtifactValidationError,
            r"^lbl: expected mapping$",
            label="lbl",
        )

    def test_require_list_valid(self) -> None:
        sample_list = [1, "two", {"item": 3}]
        self.assertEqual(require_list(sample_list, "label"), sample_list)
        self.assertEqual(require_list([], "label"), [])

    def test_require_list_invalid(self) -> None:
        invalid_types = (None, {}, {"a": 1}, "not_a_list", (1, 2), 123, True, {1, 2})
        self.assert_rejects(
            require_list,
            invalid_types,
            ArtifactValidationError,
            r"^lbl: expected list$",
            label="lbl",
        )


class TestPrLifecycleSupportRequireFields(unittest.TestCase):
    """Test require_fields validator."""

    def test_require_fields_valid(self) -> None:
        require_fields({"a": 1, "b": 2}, {"a", "b", "c"}, {"a"}, "config")
        require_fields({"a": 1}, {"a"}, {"a"}, "config")
        require_fields({}, {"a"}, set(), "config")

    def test_require_fields_unknown(self) -> None:
        with self.assertRaisesRegex(
            ValueError, r"^config: unsupported fields: \['x', 'y'\]$"
        ):
            require_fields({"a": 1, "y": 2, "x": 3}, {"a", "b"}, {"a"}, "config")

    def test_require_fields_missing(self) -> None:
        with self.assertRaisesRegex(
            ValueError, r"^config: missing required fields: \['b', 'c'\]$"
        ):
            require_fields({"a": 1}, {"a", "b", "c"}, {"a", "b", "c"}, "config")

    def test_require_fields_unknown_takes_precedence_over_missing(self) -> None:
        with self.assertRaisesRegex(
            ValueError, r"^config: unsupported fields: \['z'\]$"
        ):
            require_fields({"z": 1}, {"a", "b"}, {"a"}, "config")


class TestPrLifecycleSupportRequireUtc(BaseValidatorTest):
    """Test require_utc validator."""

    def test_require_utc_valid(self) -> None:
        for ts in (
            "2026-08-19T09:00:00Z",
            "2026-10-05T13:24:22Z",
            "2026-01-01T00:00:00.000Z",
            "2026-12-31T23:59:59.123456Z",
        ):
            with self.subTest(ts=ts):
                require_utc(ts, "ts_field")

    def test_require_utc_invalid(self) -> None:
        invalid_utc = (
            None,
            123,
            True,
            [],
            "",
            "invalid",
            "2026-08-19",
            "2026-08-19 09:00:00Z",
            "2026-08-19T09:00:00",
            "2026-08-19T09:00:00+00:00",
            "2026-08-19T09:00:00-05:00",
            "2026-08-19T09:00:00z",
            " 2026-08-19T09:00:00Z ",
            "2026-08-19T09:00:00Z\n",
        )
        self.assert_rejects(
            require_utc,
            invalid_utc,
            ValueError,
            r"^ts_field: expected RFC 3339 UTC timestamp$",
            label="ts_field",
        )


class TestPrLifecycleSupportRequireHttpsUrl(BaseValidatorTest):
    """Test require_https_url and require_https_urls validators."""

    def test_require_https_url_valid(self) -> None:
        for url in (
            "https://github.com",
            "https://github.com/abhimehro/personal-config/pull/123",
            "https://api.example.com/v1/resource?param=val#section",
        ):
            with self.subTest(url=url):
                require_https_url(url, "url_field")

    def test_require_https_url_invalid(self) -> None:
        invalid_urls = (
            None,
            123,
            True,
            [],
            "",
            "http://example.com",
            "ftp://example.com",
            "javascript:alert(1)",
            "https://",
            "https:// ",
            "https://example.com/path with spaces",
            " https://example.com",
            "https://example.com\n",
        )
        self.assert_rejects(
            require_https_url,
            invalid_urls,
            ValueError,
            r"^url_field: expected complete https URL$",
            label="url_field",
        )

    def test_require_https_urls_valid(self) -> None:
        require_https_urls([], "evidence_urls")
        require_https_urls(["https://example.com"], "evidence_urls")
        require_https_urls(
            ["https://example.com/1", "https://example.org/2"], "evidence_urls"
        )

    def test_require_https_urls_invalid_container(self) -> None:
        invalid_containers = (None, "https://example.com", {"url": "https://example.com"})
        self.assert_rejects(
            require_https_urls,
            invalid_containers,
            ArtifactValidationError,
            r"^evidence_urls: expected list$",
            label="evidence_urls",
        )

    def test_require_https_urls_invalid_items(self) -> None:
        with self.assertRaisesRegex(
            ValueError, r"^evidence_urls\[1\]: expected complete https URL$"
        ):
            require_https_urls(
                ["https://valid.com", "http://insecure.com"], "evidence_urls"
            )
        with self.assertRaisesRegex(
            ValueError, r"^evidence_urls\[0\]: expected complete https URL$"
        ):
            require_https_urls([123], "evidence_urls")


class TestPrLifecycleSupportRegexPatterns(unittest.TestCase):
    """Test regex pattern matching rules."""

    def test_sha_re(self) -> None:
        valid_sha = "0123456789abcdef0123456789abcdef01234567"
        self.assertTrue(SHA_RE.fullmatch(valid_sha))

        invalid_shas = (
            "0123456789ABCDEF0123456789ABCDEF01234567",
            "0123456789abcdef0123456789abcdef0123456",
            "0123456789abcdef0123456789abcdef012345678",
            "g" * 40,
            "",
            f" {valid_sha}",
            f"{valid_sha} ",
        )
        for s in invalid_shas:
            with self.subTest(s=s):
                self.assertIsNone(SHA_RE.fullmatch(s))

    def test_key_re(self) -> None:
        valid_sha = "a" * 40
        for k in (
            f"abhimehro/personal-config#1@{valid_sha}",
            f"owner.name/repo-name_1#9999@{valid_sha}",
        ):
            with self.subTest(k=k):
                self.assertTrue(KEY_RE.fullmatch(k))

        for k in (
            f"owner/repo#0@{valid_sha}",
            f"owner/repo#-1@{valid_sha}",
            f"owner/repo#1@{'a' * 39}",
            f"owner/repo#1@{'A' * 40}",
            f"owner#1@{valid_sha}",
            f"/repo#1@{valid_sha}",
            f"owner/repo/sub#1@{valid_sha}",
            f"owner/repo#1",
            "",
        ):
            with self.subTest(k=k):
                self.assertIsNone(KEY_RE.fullmatch(k))

    def test_utc_re(self) -> None:
        for u in (
            "2026-08-19T09:00:00Z",
            "2026-08-19T09:00:00.1Z",
            "2026-08-19T09:00:00.123456Z",
        ):
            with self.subTest(u=u):
                self.assertTrue(UTC_RE.fullmatch(u))

        for u in (
            "2026-08-19T09:00:00",
            "2026-08-19T09:00:00+00:00",
            "2026-08-19T09:00:00z",
            "2026-8-19T9:0:0Z",
            "",
        ):
            with self.subTest(u=u):
                self.assertIsNone(UTC_RE.fullmatch(u))

    def test_url_re(self) -> None:
        for url in (
            "https://github.com",
            "https://a",
            "https://example.com/path?query=1#frag",
        ):
            with self.subTest(url=url):
                self.assertTrue(URL_RE.fullmatch(url))

        for url in (
            "http://github.com",
            "https://",
            "https://example.com/a b",
            "https://example.com\n",
            "",
        ):
            with self.subTest(url=url):
                self.assertIsNone(URL_RE.fullmatch(url))


if __name__ == "__main__":
    unittest.main()
