"""Unit tests for scripts/pr_lifecycle_support.py."""

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


class TestPrLifecycleSupportMappingAndList(unittest.TestCase):
    """Test require_mapping and require_list validators."""

    def test_require_mapping_valid(self) -> None:
        """Valid dictionary inputs return the dictionary unchanged."""
        cases = ({}, {"a": 1}, {"nested": {"key": "val"}})
        for val in cases:
            with self.subTest(val=val):
                self.assertEqual(require_mapping(val, "test_label"), val)

    def test_require_mapping_invalid(self) -> None:
        """Non-dictionary inputs raise ArtifactValidationError with label."""
        invalid_cases = (
            None,
            [],
            [("a", 1)],
            "not a dict",
            123,
            True,
            False,
            {1, 2, 3},
        )
        for val in invalid_cases:
            with self.subTest(val=val):
                with self.assertRaisesRegex(
                    ArtifactValidationError, r"^my_field: expected mapping$"
                ):
                    require_mapping(val, "my_field")

    def test_require_list_valid(self) -> None:
        """Valid list inputs return the list unchanged."""
        cases = ([], [1, 2, 3], [{"item": "val"}])
        for val in cases:
            with self.subTest(val=val):
                self.assertEqual(require_list(val, "test_label"), val)

    def test_require_list_invalid(self) -> None:
        """Non-list inputs raise ArtifactValidationError with label."""
        invalid_cases = (
            None,
            {},
            {"a": 1},
            "not a list",
            (1, 2, 3),
            123,
            True,
            False,
            {1, 2, 3},
        )
        for val in invalid_cases:
            with self.subTest(val=val):
                with self.assertRaisesRegex(
                    ArtifactValidationError, r"^my_field: expected list$"
                ):
                    require_list(val, "my_field")


class TestPrLifecycleSupportRequireFields(unittest.TestCase):
    """Test require_fields validator."""

    def test_require_fields_valid(self) -> None:
        """Allowed and required fields satisfied without unknown fields."""
        require_fields(
            value={"a": 1, "b": 2},
            allowed={"a", "b", "c"},
            required={"a"},
            label="config",
        )
        # Exactly required and allowed
        require_fields(
            value={"a": 1},
            allowed={"a"},
            required={"a"},
            label="config",
        )
        # Empty dict with empty required
        require_fields(
            value={},
            allowed={"a"},
            required=set(),
            label="config",
        )

    def test_require_fields_unknown(self) -> None:
        """Unsupported fields raise ValueError with sorted unknown field names."""
        with self.assertRaisesRegex(
            ValueError, r"^config: unsupported fields: \['x', 'y'\]$"
        ):
            require_fields(
                value={"a": 1, "y": 2, "x": 3},
                allowed={"a", "b"},
                required={"a"},
                label="config",
            )

    def test_require_fields_missing(self) -> None:
        """Missing required fields raise ValueError with sorted missing field names."""
        with self.assertRaisesRegex(
            ValueError, r"^config: missing required fields: \['b', 'c'\]$"
        ):
            require_fields(
                value={"a": 1},
                allowed={"a", "b", "c"},
                required={"a", "b", "c"},
                label="config",
            )

    def test_require_fields_unknown_takes_precedence_over_missing(self) -> None:
        """When unknown and missing fields coexist, unsupported fields error is raised first."""
        with self.assertRaisesRegex(
            ValueError, r"^config: unsupported fields: \['z'\]$"
        ):
            require_fields(
                value={"z": 1},
                allowed={"a", "b"},
                required={"a"},
                label="config",
            )


class TestPrLifecycleSupportRequireUtc(unittest.TestCase):
    """Test require_utc validator."""

    def test_require_utc_valid(self) -> None:
        """Valid RFC 3339 UTC timestamps pass without error."""
        valid_timestamps = (
            "2026-08-19T09:00:00Z",
            "2026-10-05T13:24:22Z",
            "2026-01-01T00:00:00.000Z",
            "2026-12-31T23:59:59.123456Z",
        )
        for ts in valid_timestamps:
            with self.subTest(ts=ts):
                require_utc(ts, "created_at_utc")

    def test_require_utc_invalid_non_string(self) -> None:
        """Non-string values raise ValueError with label."""
        non_strings = (None, 123, 123.45, True, False, [], {})
        for val in non_strings:
            with self.subTest(val=val):
                with self.assertRaisesRegex(
                    ValueError, r"^updated_at_utc: expected RFC 3339 UTC timestamp$"
                ):
                    require_utc(val, "updated_at_utc")

    def test_require_utc_invalid_formats(self) -> None:
        """Malformed, non-UTC, or offset timestamps raise ValueError."""
        invalid_formats = (
            "",
            "not-a-timestamp",
            "2026-08-19",
            "2026-08-19 09:00:00Z",
            "2026-08-19T09:00:00",
            "2026-08-19T09:00:00+00:00",
            "2026-08-19T09:00:00-05:00",
            "2026-08-19T09:00:00z",
            " 2026-08-19T09:00:00Z ",
            "2026-08-19T09:00:00Z\n",
        )
        for ts in invalid_formats:
            with self.subTest(ts=ts):
                with self.assertRaisesRegex(
                    ValueError, r"^timestamp: expected RFC 3339 UTC timestamp$"
                ):
                    require_utc(ts, "timestamp")


class TestPrLifecycleSupportRequireHttpsUrl(unittest.TestCase):
    """Test require_https_url and require_https_urls validators."""

    def test_require_https_url_valid(self) -> None:
        """Complete https URLs pass without error."""
        valid_urls = (
            "https://github.com",
            "https://github.com/abhimehro/personal-config/pull/123",
            "https://api.example.com/v1/resource?param=val#section",
        )
        for url in valid_urls:
            with self.subTest(url=url):
                require_https_url(url, "evidence_url")

    def test_require_https_url_invalid_non_string(self) -> None:
        """Non-string values raise ValueError with label."""
        non_strings = (None, 123, True, False, ["https://example.com"], {})
        for val in non_strings:
            with self.subTest(val=val):
                with self.assertRaisesRegex(
                    ValueError, r"^evidence_url: expected complete https URL$"
                ):
                    require_https_url(val, "evidence_url")

    def test_require_https_url_invalid_schemes_and_formats(self) -> None:
        """Non-https schemes, whitespace, missing netloc raise ValueError."""
        invalid_urls = (
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
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaisesRegex(
                    ValueError, r"^evidence_url: expected complete https URL$"
                ):
                    require_https_url(url, "evidence_url")

    def test_require_https_urls_valid(self) -> None:
        """Lists of complete https URLs pass without error."""
        cases = (
            [],
            ["https://example.com"],
            [
                "https://example.com/one",
                "https://example.org/two",
            ],
        )
        for urls in cases:
            with self.subTest(urls=urls):
                require_https_urls(urls, "evidence_urls")

    def test_require_https_urls_invalid_container(self) -> None:
        """Non-list containers raise ArtifactValidationError."""
        invalid_containers = (None, "https://example.com", {"url": "https://example.com"})
        for container in invalid_containers:
            with self.subTest(container=container):
                with self.assertRaisesRegex(
                    ArtifactValidationError, r"^evidence_urls: expected list$"
                ):
                    require_https_urls(container, "evidence_urls")

    def test_require_https_urls_invalid_items(self) -> None:
        """Invalid URL in list raises ValueError with indexed label."""
        with self.assertRaisesRegex(
            ValueError, r"^evidence_urls\[1\]: expected complete https URL$"
        ):
            require_https_urls(
                ["https://valid.com", "http://insecure.com"],
                "evidence_urls",
            )
        with self.assertRaisesRegex(
            ValueError, r"^evidence_urls\[0\]: expected complete https URL$"
        ):
            require_https_urls([123], "evidence_urls")


class TestPrLifecycleSupportRegexPatterns(unittest.TestCase):
    """Test regex pattern matching rules."""

    def test_sha_re(self) -> None:
        """SHA_RE matches 40-character lowercase hex strings."""
        valid_sha = "0123456789abcdef0123456789abcdef01234567"
        self.assertTrue(SHA_RE.fullmatch(valid_sha))

        invalid_shas = (
            "0123456789ABCDEF0123456789ABCDEF01234567",  # uppercase
            "0123456789abcdef0123456789abcdef0123456",   # 39 chars
            "0123456789abcdef0123456789abcdef012345678",  # 41 chars
            "g" * 40,                                     # non-hex
            "",
            f" {valid_sha}",
            f"{valid_sha} ",
        )
        for s in invalid_shas:
            with self.subTest(s=s):
                self.assertIsNone(SHA_RE.fullmatch(s))

    def test_key_re(self) -> None:
        """KEY_RE matches owner/repo#pr@sha item keys."""
        valid_sha = "a" * 40
        valid_keys = (
            f"abhimehro/personal-config#1@{valid_sha}",
            f"owner.name/repo-name_1#9999@{valid_sha}",
        )
        for k in valid_keys:
            with self.subTest(k=k):
                self.assertTrue(KEY_RE.fullmatch(k))

        invalid_keys = (
            f"owner/repo#0@{valid_sha}",          # PR 0 is invalid
            f"owner/repo#-1@{valid_sha}",         # Negative PR
            f"owner/repo#1@{'a' * 39}",          # Short SHA
            f"owner/repo#1@{'A' * 40}",          # Uppercase SHA
            f"owner#1@{valid_sha}",               # Missing repo
            f"/repo#1@{valid_sha}",               # Missing owner
            f"owner/repo/sub#1@{valid_sha}",      # Extra path segment
            f"owner/repo#1",                      # Missing @sha
            "",
        )
        for k in invalid_keys:
            with self.subTest(k=k):
                self.assertIsNone(KEY_RE.fullmatch(k))

    def test_utc_re(self) -> None:
        """UTC_RE matches RFC 3339 UTC strings with optional fractional seconds."""
        valid_utc = (
            "2026-08-19T09:00:00Z",
            "2026-08-19T09:00:00.1Z",
            "2026-08-19T09:00:00.123456Z",
        )
        for u in valid_utc:
            with self.subTest(u=u):
                self.assertTrue(UTC_RE.fullmatch(u))

        invalid_utc = (
            "2026-08-19T09:00:00",
            "2026-08-19T09:00:00+00:00",
            "2026-08-19T09:00:00z",
            "2026-8-19T9:0:0Z",
            "",
        )
        for u in invalid_utc:
            with self.subTest(u=u):
                self.assertIsNone(UTC_RE.fullmatch(u))

    def test_url_re(self) -> None:
        """URL_RE matches strings starting with https:// and containing no whitespace."""
        valid_urls = (
            "https://github.com",
            "https://a",
            "https://example.com/path?query=1#frag",
        )
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(URL_RE.fullmatch(url))

        invalid_urls = (
            "http://github.com",
            "https://",
            "https://example.com/a b",
            "https://example.com\n",
            "",
        )
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertIsNone(URL_RE.fullmatch(url))


if __name__ == "__main__":
    unittest.main()
