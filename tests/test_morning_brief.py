#!/usr/bin/env python3
"""
Unit tests for the pure helpers in morning-brief.py.

Run with:
    python3 -m unittest tests.test_morning_brief -v
    # or: python3 -m pytest test_morning_brief.py -v  (optional dev dependency)
"""

import datetime as dt
import importlib.util
import os
import sys as _sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Adjust import path if needed (e.g., if script is in scripts/morning-brief/)
# sys.path.insert(0, str(Path(__file__).resolve().parent))


def _install_morning_brief_import_stubs() -> None:
    """CI runs unittest with stdlib only; morning-brief.py imports pip deps at top level.

    Pure helpers under test do not need real feedparser/requests/dotenv. Stub them so
    the module loads; integration behavior is not covered here.
    """
    if "feedparser" not in _sys.modules:
        _fp = types.ModuleType("feedparser")

        def _parse(*_a, **_kw):  # noqa: ANN002, ANN003
            return types.SimpleNamespace(entries=[])

        _fp.parse = _parse
        _sys.modules["feedparser"] = _fp

    if "dotenv" not in _sys.modules:
        _de = types.ModuleType("dotenv")
        _de.load_dotenv = lambda *_a, **_kw: None  # noqa: ANN002, ANN003
        _sys.modules["dotenv"] = _de

    if "requests" not in _sys.modules:
        _rq = types.ModuleType("requests")

        class _Session:
            pass

        _rq.Session = _Session
        _rq.utils = types.SimpleNamespace(
            quote=lambda s, safe="": s,
        )
        _sys.modules["requests"] = _rq

    if "requests.adapters" not in _sys.modules:
        _ad = types.ModuleType("requests.adapters")

        class HTTPAdapter:  # noqa: D101
            def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
                pass

        _ad.HTTPAdapter = HTTPAdapter
        _sys.modules["requests.adapters"] = _ad

    _sys.modules.setdefault("urllib3", types.ModuleType("urllib3"))
    _sys.modules.setdefault("urllib3.util", types.ModuleType("urllib3.util"))
    if "urllib3.util.retry" not in _sys.modules:
        _ur = types.ModuleType("urllib3.util.retry")

        class Retry:  # noqa: D101
            def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
                pass

        _ur.Retry = Retry
        _sys.modules["urllib3.util.retry"] = _ur


_install_morning_brief_import_stubs()

# Import the script by file path — handles the hyphenated module name
_script = (
    Path(__file__).parent.parent / "scripts" / "morning-brief" / "morning-brief.py"
)
_spec = importlib.util.spec_from_file_location("morning_brief", _script)
mb = importlib.util.module_from_spec(_spec)
_sys.modules["morning_brief"] = mb
_spec.loader.exec_module(mb)


# ===== Text Helpers =====
class TestTextHelpers(unittest.TestCase):
    """Grouped tests for text sanitization, truncation, HTML stripping, and HTML helpers."""

    def test_sanitize_text_none(self):
        assert mb.sanitize_text(None) == ""

    def test_sanitize_text_plain(self):
        assert mb.sanitize_text("hello") == "hello"

    def test_sanitize_text_html_entities(self):
        assert mb.sanitize_text('<script>alert("xss")</script>') == (
            "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;"
        )

    def test_sanitize_text_strips_whitespace(self):
        assert mb.sanitize_text("  padded  ") == "padded"

    def test_sanitize_text_numeric_input(self):
        assert mb.sanitize_text(42) == "42"

    def test_sanitize_text_ampersand(self):
        assert mb.sanitize_text("A & B") == "A &amp; B"

    def test_truncate_text_short_text_unchanged(self):
        assert mb.truncate_text("short", 100) == "short"

    def test_truncate_text_exact_length(self):
        text = "a" * 150
        assert mb.truncate_text(text, 150) == text

    def test_truncate_text_long_text_truncated(self):
        text = "a" * 200
        result = mb.truncate_text(text, 150)
        assert result.endswith("...")
        assert len(result) == 150

    def test_truncate_text_empty(self):
        assert mb.truncate_text("", 10) == ""

    def test_truncate_text_none(self):
        assert mb.truncate_text(None, 10) == ""

    def test_strip_html_tags_removes_tags(self):
        assert mb.strip_html_tags("<p>Hello <b>world</b></p>") == "Hello world"

    def test_strip_html_tags_empty(self):
        assert mb.strip_html_tags("") == ""

    def test_strip_html_tags_no_tags(self):
        assert mb.strip_html_tags("plain text") == "plain text"

    def test_strip_html_tags_nested_tags(self):
        assert mb.strip_html_tags("<div><p><span>deep</span></p></div>") == "deep"

    def test_html_li(self):
        assert mb.html_li("content") == "<li>content</li>"

    def test_html_ul(self):
        items = ["<li>a</li>", "<li>b</li>"]
        assert mb.html_ul(items) == "<ul><li>a</li><li>b</li></ul>"

    def test_html_ul_empty(self):
        assert (
            mb.html_ul([])
            == '<ul><li class="empty-state"><span aria-hidden="true">📭</span> <span role="status">No items <span class="hint" style="font-size: 0.9em; color: #6c757d; margin-left: 8px;">(Check <kbd>~/.config/morning-brief.env</kbd> configuration)</span></span></li></ul>'
        )

    def test_html_section(self):
        result = mb.html_section("Title", "<p>body</p>")
        assert '<section role="region" aria-labelledby="title">' in result
        assert '<h3 id="title">Title</h3>' in result
        assert "<p>body</p>" in result

    def test_html_section_escapes_title(self):
        result = mb.html_section("<script>", "<p>safe</p>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        assert 'aria-labelledby="lt-script-gt"' in result

    def test_html_section_with_emoji(self):
        result = mb.html_section("🌅 Good Morning", "<p>body</p>")
        assert "aria-label=" not in result
        assert '<span aria-hidden="true">🌅</span>' in result
        assert 'id="good-morning"' in result
        assert "Good Morning</h3>" in result

    def test_html_section_non_ascii_text(self):
        result = mb.html_section("Café Menu", "<p>body</p>")
        assert "aria-label=" not in result
        assert '<span aria-hidden="true">' not in result
        assert '<h3 id="caf-menu">Café Menu</h3>' in result


# ===== Date Helpers =====
class TestDateHelpers(unittest.TestCase):
    """Grouped tests for date-related helpers, horoscope extraction, and staleness calculation."""

    def test_is_due_today_matches(self):
        assert mb.is_due_today("2026-03-25", "2026-03-25") is True

    def test_is_due_today_no_match(self):
        assert mb.is_due_today("2026-03-26", "2026-03-25") is False

    def test_is_due_today_empty(self):
        assert mb.is_due_today("", "2026-03-25") is False

    def test_is_due_today_none_like(self):
        assert mb.is_due_today(None, "2026-03-25") is False

    def test_extract_horoscope_text_nested_data(self):
        payload = {"data": {"horoscope_data": "Stars align."}}
        assert mb.extract_horoscope_text(payload) == "Stars align."

    def test_extract_horoscope_text_flat_horoscope(self):
        assert mb.extract_horoscope_text({"horoscope": "Be bold."}) == "Be bold."

    def test_extract_horoscope_text_description_fallback(self):
        assert (
            mb.extract_horoscope_text({"description": "Trust yourself."})
            == "Trust yourself."
        )

    def test_extract_horoscope_text_empty_dict(self):
        assert mb.extract_horoscope_text({}) is None

    def test_extract_horoscope_text_non_dict(self):
        assert mb.extract_horoscope_text("not a dict") is None

    def test_extract_horoscope_text_whitespace_only(self):
        assert mb.extract_horoscope_text({"horoscope": "   "}) is None

    def test_extract_horoscope_text_flat_horoscope_data(self):
        assert (
            mb.extract_horoscope_text({"horoscope_data": "Flat data."}) == "Flat data."
        )

    def test_extract_horoscope_text_priority_order(self):
        payload = {
            "data": {"horoscope_data": "Priority 1"},
            "horoscope_data": "Priority 2",
            "horoscope": "Priority 3",
            "description": "Priority 4",
        }
        assert mb.extract_horoscope_text(payload) == "Priority 1"

        del payload["data"]
        assert mb.extract_horoscope_text(payload) == "Priority 2"

        del payload["horoscope_data"]
        assert mb.extract_horoscope_text(payload) == "Priority 3"

    def test_extract_horoscope_text_non_string_candidates(self):
        payload = {
            "horoscope_data": 123,
            "horoscope": ["not", "a", "string"],
            "description": "The only string.",
        }
        assert mb.extract_horoscope_text(payload) == "The only string."

    def test_extract_horoscope_text_nested_not_dict(self):
        # If 'data' is a string, it shouldn't crash nested.get
        payload = {"data": "not-a-dict", "horoscope": "Fallback."}
        assert mb.extract_horoscope_text(payload) == "Fallback."

    def test_staleness_zero_for_today(self):
        assert mb.staleness_days("2026-03-25T12:00:00Z", dt.date(2026, 3, 25)) == 0

    def test_staleness_positive_days(self):
        assert mb.staleness_days("2026-03-20T12:00:00Z", dt.date(2026, 3, 25)) == 5

    def test_staleness_empty_string(self):
        assert mb.staleness_days("", dt.date(2026, 3, 25)) == 0

    def test_staleness_invalid_format(self):
        assert mb.staleness_days("not-a-date", dt.date(2026, 3, 25)) == 0

    def test_staleness_future_date(self):
        assert mb.staleness_days("2026-03-30T12:00:00Z", dt.date(2026, 3, 25)) == 0


# ===== Linear Scoring =====
class TestLinearScoring(unittest.TestCase):
    """Grouped tests for Linear issue scoring."""

    TODAY_ISO = "2026-03-25"
    TODAY_DATE = dt.date(2026, 3, 25)

    def _issue(self, **overrides):
        base = {
            "priority": 0,
            "dueDate": None,
            "state": {"name": "Open", "type": "unstarted"},
            "labels": {"nodes": []},
            "updatedAt": "2026-03-25T00:00:00Z",
            "cycle": None,
        }
        base.update(overrides)
        return base

    def test_due_today_urgent(self):
        issue = self._issue(priority=1, dueDate=self.TODAY_ISO)
        score = mb.score_linear_issue(issue, self.TODAY_ISO, self.TODAY_DATE)
        assert score >= 180  # 100 + 80 + state

    def test_no_priority_no_due(self):
        issue = self._issue()
        score = mb.score_linear_issue(issue, self.TODAY_ISO, self.TODAY_DATE)
        assert score >= 0
        assert score < 50

    def test_started_state_bonus(self):
        issue = self._issue(state={"name": "In Progress", "type": "started"})
        score_started = mb.score_linear_issue(issue, self.TODAY_ISO, self.TODAY_DATE)
        issue_backlog = self._issue(state={"name": "Backlog", "type": "backlog"})
        score_backlog = mb.score_linear_issue(
            issue_backlog, self.TODAY_ISO, self.TODAY_DATE
        )
        assert score_started > score_backlog

    def test_label_bonus(self):
        issue_bug = self._issue(labels={"nodes": [{"name": "Bug"}]})
        issue_plain = self._issue()
        assert mb.score_linear_issue(
            issue_bug, self.TODAY_ISO, self.TODAY_DATE
        ) > mb.score_linear_issue(issue_plain, self.TODAY_ISO, self.TODAY_DATE)

    def test_staleness_penalty(self):
        issue_stale = self._issue(updatedAt="2026-02-01T00:00:00Z")
        issue_fresh = self._issue(updatedAt="2026-03-24T00:00:00Z")
        assert mb.score_linear_issue(
            issue_fresh, self.TODAY_ISO, self.TODAY_DATE
        ) >= mb.score_linear_issue(issue_stale, self.TODAY_ISO, self.TODAY_DATE)

    def test_cycle_bonus(self):
        issue_cycle = self._issue(cycle={"id": "abc"})
        issue_no_cycle = self._issue()
        assert mb.score_linear_issue(
            issue_cycle, self.TODAY_ISO, self.TODAY_DATE
        ) > mb.score_linear_issue(issue_no_cycle, self.TODAY_ISO, self.TODAY_DATE)

    def test_score_never_negative(self):
        issue = self._issue(updatedAt="2020-01-01T00:00:00Z")
        assert mb.score_linear_issue(issue, self.TODAY_ISO, self.TODAY_DATE) >= 0

    def test_missing_fields(self):
        """Issues with completely missing fields should not crash."""
        score = mb.score_linear_issue({}, self.TODAY_ISO, self.TODAY_DATE)
        assert isinstance(score, int)
        assert score >= 0


# ===== Focus and Selection =====
class TestFocusAndSelection(unittest.TestCase):
    """Grouped tests for focus meta, selection, dynamic tag inference, time-aware guidance, and GitHub context notes."""

    def test_build_focus_meta_parts_full_item(self):
        item = mb.FocusItem(
            kind="linear",
            identifier="ENG-1",
            title="Fix bug",
            url="#",
            badge="urgent",
            state="In Progress",
            due_date="2026-03-25",
            time_label="",
        )
        parts = mb.build_focus_meta_parts(item, "2026-03-25")
        assert "urgent" in parts
        assert "In Progress" in parts
        assert "due today" in parts

    def test_build_focus_meta_parts_empty_item(self):
        item = mb.FocusItem(kind="linear", identifier="", title="", url="#")
        assert mb.build_focus_meta_parts(item, "2026-03-25") == []

    def test_select_focus_pair_both_available(self):
        li = [mb.FocusItem(kind="linear", identifier="A", title="t", url="#")]
        ci = [mb.FocusItem(kind="calendar", identifier="B", title="t", url="#")]
        deep, admin = mb.select_focus_pair(li, ci)
        assert deep is not None
        assert admin is not None

    def test_select_focus_pair_both_empty(self):
        deep, admin = mb.select_focus_pair([], [])
        assert deep is None
        assert admin is None

    def test_build_selection_reason_no_item_deep(self):
        result = mb.build_selection_reason("deep work", None, "2026-03-25")
        assert "general planning" in result

    def test_build_selection_reason_no_item_admin(self):
        result = mb.build_selection_reason("admin", None, "2026-03-25")
        assert "housekeeping" in result

    def test_build_selection_reason_linear_due_today(self):
        item = mb.FocusItem(
            kind="linear", identifier="X", title="t", url="#", due_date="2026-03-25"
        )
        result = mb.build_selection_reason("deep work", item, "2026-03-25")
        assert "due today" in result

    def test_build_selection_reason_calendar_item(self):
        item = mb.FocusItem(
            kind="calendar", identifier="C", title="t", url="#", time_label="09:00"
        )
        result = mb.build_selection_reason("admin", item, "2026-03-25")
        assert "time block" in result

    def test_derive_dynamic_tags_coastal_keyword(self):
        assert "coastal-science" in mb.derive_dynamic_tags(
            "The coastal wetland study results"
        )

    def test_derive_dynamic_tags_no_match(self):
        assert mb.derive_dynamic_tags("Regular news about nothing relevant") == []

    def test_derive_dynamic_tags_empty(self):
        assert mb.derive_dynamic_tags("") == []

    def test_time_aware_guidance_morning(self):
        result = mb.get_time_aware_guidance(dt.datetime(2026, 3, 25, 8, 0))
        assert "deep work" in result.lower()

    def test_time_aware_guidance_midday(self):
        result = mb.get_time_aware_guidance(dt.datetime(2026, 3, 25, 13, 0))
        assert "handoff" in result.lower()

    def test_time_aware_guidance_evening(self):
        result = mb.get_time_aware_guidance(dt.datetime(2026, 3, 25, 18, 0))
        assert "lighter" in result.lower()

    def test_github_context_note_linear_deep(self):
        item = mb.FocusItem(kind="linear", identifier="X", title="t", url="#")
        result = mb.build_github_context_note(item, None)
        assert "admin block" in result

    def test_github_context_note_calendar_admin(self):
        item = mb.FocusItem(kind="calendar", identifier="C", title="t", url="#")
        result = mb.build_github_context_note(None, item)
        assert "GitHub sweep" in result

    def test_github_context_note_fallback(self):
        result = mb.build_github_context_note(None, None)
        assert "admin slot" in result


# ===== Environment and Cache =====
class TestEnvironmentAndCache(unittest.TestCase):
    """Grouped tests for environment helpers, cache, API key validation, client validation, app config, DailyContext, SectionToggles, podcast, and weather."""

    def test_env_bool_defaults_true(self):
        assert mb._env_bool("NONEXISTENT_KEY_XYZ_123", True) is True

    def test_env_bool_defaults_false(self):
        assert mb._env_bool("NONEXISTENT_KEY_XYZ_123", False) is False

    def test_env_bool_empty_string(self):
        os.environ["_TEST_BOOL"] = ""
        assert mb._env_bool("_TEST_BOOL", True) is True
        assert mb._env_bool("_TEST_BOOL", False) is False
        del os.environ["_TEST_BOOL"]

    def test_env_bool_whitespace_string(self):
        os.environ["_TEST_BOOL"] = "   "
        assert mb._env_bool("_TEST_BOOL", True) is True
        assert mb._env_bool("_TEST_BOOL", False) is False
        del os.environ["_TEST_BOOL"]

    def test_env_bool_unrecognized_value(self):
        os.environ["_TEST_BOOL"] = "unknown"
        # Anything not explicitly false is true.
        assert mb._env_bool("_TEST_BOOL", False) is True
        del os.environ["_TEST_BOOL"]

    def test_env_bool_false_values(self):
        for val in ("0", "false", "no", "off", "disabled"):
            os.environ["_TEST_BOOL"] = val
            assert mb._env_bool("_TEST_BOOL", True) is False
            del os.environ["_TEST_BOOL"]

    def test_env_bool_true_values(self):
        for val in ("1", "true", "yes", "on"):
            os.environ["_TEST_BOOL"] = val
            assert mb._env_bool("_TEST_BOOL", False) is True
            del os.environ["_TEST_BOOL"]

    def test_safe_int_valid(self):
        os.environ["_TEST_INT"] = "42"
        assert mb._safe_int("_TEST_INT", 10) == 42
        del os.environ["_TEST_INT"]

    def test_safe_int_negative(self):
        os.environ["_TEST_INT"] = "-42"
        assert mb._safe_int("_TEST_INT", 10) == -42
        del os.environ["_TEST_INT"]

    def test_safe_int_padded_int(self):
        os.environ["_TEST_INT"] = "  42  "
        assert mb._safe_int("_TEST_INT", 10) == 42
        del os.environ["_TEST_INT"]

    def test_safe_int_empty_string(self):
        os.environ["_TEST_INT"] = ""
        assert mb._safe_int("_TEST_INT", 10) == 10
        del os.environ["_TEST_INT"]

    def test_safe_int_whitespace_string(self):
        os.environ["_TEST_INT"] = "   "
        assert mb._safe_int("_TEST_INT", 10) == 10
        del os.environ["_TEST_INT"]

    def test_safe_int_float_fallback(self):
        os.environ["_TEST_INT"] = "3.14"
        assert mb._safe_int("_TEST_INT", 10) == 10
        del os.environ["_TEST_INT"]

    def test_safe_int_invalid(self):
        os.environ["_TEST_INT"] = "abc"
        assert mb._safe_int("_TEST_INT", 10) == 10
        del os.environ["_TEST_INT"]

    def test_safe_int_missing(self):
        assert mb._safe_int("_MISSING_KEY_123", 5) == 5

    def test_file_cache_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cache = mb.FileCache(str(Path(td) / "cache"))
            cache.set("test-key", {"hello": "world"})
            result = cache.get("test-key", ttl=60)
            self.assertEqual(result, {"hello": "world"})

    def test_file_cache_expired(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cache = mb.FileCache(str(Path(td) / "cache"))
            cache.set("test-key", "value")
            result = cache.get("test-key", ttl=0)
            self.assertIsNone(result)

    def test_file_cache_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cache = mb.FileCache(str(Path(td) / "cache"))
            self.assertIsNone(cache.get("nonexistent", ttl=60))

    def test_file_cache_corrupted_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cache = mb.FileCache(str(Path(td) / "cache"))
            cache.set("test-key", "value")
            path = cache._key_path("test-key")
            path.write_text("NOT VALID JSON", encoding="utf-8")
            self.assertIsNone(cache.get("test-key", ttl=60))

    def test_file_cache_string_value(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cache = mb.FileCache(str(Path(td) / "cache"))
            cache.set("html", "<h1>Hello</h1>")
            self.assertEqual(cache.get("html", ttl=60), "<h1>Hello</h1>")

    def test_valid_api_keys(self):
        valid_keys = [
            "lin_api_abcdef1234567890",
            "pplx_TEST_NOT_A_REAL_KEY1234567890",
            "Token1234567890",
            "readwise_live_token_12345678",
            "secret:key.123+456/789=foo_bar-baz",
        ]
        for key in valid_keys:
            with self.subTest(key=key):
                self.assertEqual(mb._validate_api_key(key), key)

    def test_whitespace_stripped(self):
        self.assertEqual(
            mb._validate_api_key("   pplx_TEST_NOT_A_REAL_KEY   "),
            "pplx_TEST_NOT_A_REAL_KEY",
        )

    def test_empty_and_non_string(self):
        self.assertEqual(mb._validate_api_key(""), "")
        self.assertEqual(mb._validate_api_key("    "), "")
        self.assertEqual(mb._validate_api_key(None), "")
        self.assertEqual(mb._validate_api_key(123456789), "")
        self.assertEqual(mb._validate_api_key(["token"]), "")

    def test_crlf_injection_rejected(self):
        injections = [
            "valid_token_12345\r\nInjected-Header: evil",
            "valid_token_12345\nInjected-Header: evil",
            "valid_token_12345\rInjected-Header: evil",
        ]
        for key in injections:
            with self.subTest(key=key):
                self.assertEqual(mb._validate_api_key(key), "")

    def test_placeholder_rejected(self):
        placeholders = [
            "REPLACE_WITH_YOUR_PERPLEXITY_API_KEY",
            "replace_with_linear_token",
            "your_api_key_here",
            "none",
            "null",
            "dummy_api_key",
            "example_token",
            "<YOUR_API_KEY>",
            "*****************",
        ]
        for ph in placeholders:
            with self.subTest(ph=ph):
                self.assertEqual(mb._validate_api_key(ph), "")

    def test_invalid_chars_or_length_rejected(self):
        invalid_keys = [
            "short",  # under 8 chars
            "token with spaces inside 123",
            "key_with_quotes'123456",
            'key_with_double_quotes"123456',
            "key_with_semicolon;123456",
            "key_with_backtick`123456",
            "a" * 513,  # exceeds 512 chars
        ]
        for key in invalid_keys:
            with self.subTest(key=key):
                self.assertEqual(mb._validate_api_key(key), "")

    def test_perplexity_client_validates_key(self):
        # Valid key
        client = mb.PerplexityClient("pplx_TEST_NOT_A_REAL_KEY")
        self.assertTrue(client.enabled)
        self.assertEqual(client.api_key, "pplx_TEST_NOT_A_REAL_KEY")

        # CRLF injection rejected
        bad_client = mb.PerplexityClient("pplx-12345\r\nEvil: true")
        self.assertFalse(bad_client.enabled)
        self.assertEqual(bad_client.api_key, "")

        # Empty / whitespace key
        empty_client = mb.PerplexityClient("   ")
        self.assertFalse(empty_client.enabled)
        self.assertEqual(empty_client.api_key, "")

    def test_app_config_load_fallbacks(self):
        # Test fallback for Perplexity (PPLX_API_KEY) and Linear (LINEAR_TOKEN)
        env = {
            "READWISE_TOKEN": "readwise_valid_token_12345",
            "PPLX_API_KEY": "pplx-valid-token-from-fallback",
            "LINEAR_TOKEN": "lin_api_valid_token_fallback",
        }
        # Ensure primary keys are unset
        for k in ("PERPLEXITY_API_KEY", "LINEAR_API_KEY", "READWISE_API_KEY"):
            os.environ.pop(k, None)

        with patch.dict(os.environ, env, clear=False):
            config = mb.AppConfig.load(argv=["--dry-run"])
            self.assertEqual(config.readwise_token, "readwise_valid_token_12345")
            self.assertEqual(
                config.perplexity_api_key, "pplx-valid-token-from-fallback"
            )
            self.assertEqual(config.linear_api_key, "lin_api_valid_token_fallback")

    def test_app_config_load_primary_precedence(self):
        # Primary takes precedence over fallback
        env = {
            "READWISE_TOKEN": "readwise_primary_12345",
            "READWISE_API_KEY": "readwise_fallback_12345",
            "PERPLEXITY_API_KEY": "pplx_TEST_NOT_A_REAL_KEY_2",
            "PPLX_API_KEY": "pplx-fallback-12345678",
            "LINEAR_API_KEY": "lin_TEST_NOT_A_REAL_KEY",
            "LINEAR_TOKEN": "lin_api_fallback_12345",
        }

        with patch.dict(os.environ, env, clear=False):
            config = mb.AppConfig.load(argv=["--dry-run"])
            self.assertEqual(config.readwise_token, "readwise_primary_12345")
            self.assertEqual(config.perplexity_api_key, "pplx_TEST_NOT_A_REAL_KEY_2")
            self.assertEqual(config.linear_api_key, "lin_TEST_NOT_A_REAL_KEY")

    def test_app_config_load_filters_malformed_keys(self):
        env = {
            "READWISE_TOKEN": "valid_readwise_token_12345",
            "PERPLEXITY_API_KEY": "pplx-invalid\r\nHeader: inject",
            "LINEAR_API_KEY": "REPLACE_WITH_YOUR_KEY",
        }

        with patch.dict(os.environ, env, clear=False):
            config = mb.AppConfig.load(argv=["--dry-run"])
            self.assertEqual(config.readwise_token, "valid_readwise_token_12345")
            self.assertEqual(config.perplexity_api_key, "")
            self.assertEqual(config.linear_api_key, "")

    @patch('scripts.morning_brief.morning_brief.SectionToggles')
    @patch('scripts.morning_brief.morning_brief.AppConfig')
    def test_daily_context_initialization(self, mock_app_config, mock_section_toggles):
        """Test DailyContext initialization."""
        mock_app_config.return_value.load.return_value = {
            'WEATHER_API_KEY': 'test_weather_key',
            'PODCAST_API_KEY': 'test_podcast_key',
            'LINEAR_API_KEY': 'test_linear_key',
            'GITHUB_TOKEN': 'test_github_token'
        }
        mock_section_toggles.return_value = Mock()

        context = mb.DailyContext()
        self.assertEqual(context.weather_api_key, 'test_weather_key')
        self.assertEqual(context.podcast_api_key, 'test_podcast_key')
        self.assertEqual(context.linear_api_key, 'test_linear_key')
        self.assertEqual(context.github_token, 'test_github_token')
        self.assertIsNone(context.weather_data)
        self.assertIsNone(context.podcast_data)
        self.assertIsNone(context.linear_data)
        self.assertIsNone(context.github_notes)

    @patch('scripts.morning_brief.morning_brief.fetch_weather_data')
    def test_fetch_weather_success(self, mock_fetch):
        """Test successful weather data fetch."""
        mock_fetch.return_value = {'temp': 72}
        context = mb.DailyContext()
        context.weather_api_key = 'test_key'
        context.fetch_weather()
        self.assertEqual(context.weather_data, {'temp': 72})

    @patch('scripts.morning_brief.morning_brief.fetch_weather_data')
    def test_fetch_weather_failure(self, mock_fetch):
        """Test failed weather data fetch."""
        mock_fetch.side_effect = Exception('API Error')
        context = mb.DailyContext()
        context.weather_api_key = 'test_key'
        context.fetch_weather()
        self.assertIsNone(context.weather_data)

    @patch('scripts.morning_brief.morning_brief.fetch_podcast_data')
    def test_fetch_podcast_success(self, mock_fetch):
        """Test successful podcast data fetch."""
        mock_fetch.return_value = {'title': 'Test Podcast'}
        context = mb.DailyContext()
        context.podcast_api_key = 'test_key'
        context.fetch_podcast()
        self.assertEqual(context.podcast_data, {'title': 'Test Podcast'})

    @patch('scripts.morning_brief.morning_brief.fetch_podcast_data')
    def test_fetch_podcast_failure(self, mock_fetch):
        """Test failed podcast data fetch."""
        mock_fetch.side_effect = Exception('API Error')
        context = mb.DailyContext()
        context.podcast_api_key = 'test_key'
        context.fetch_podcast()
        self.assertIsNone(context.podcast_data)

    @patch('scripts.morning_brief.morning_brief.fetch_linear_data')
    def test_fetch_linear_success(self, mock_fetch):
        """Test successful Linear data fetch."""
        mock_fetch.return_value = {'issues': []}
        context = mb.DailyContext()
        context.linear_api_key = 'test_key'
        context.fetch_linear()
        self.assertEqual(context.linear_data, {'issues': []})

    @patch('scripts.morning_brief.morning_brief.fetch_linear_data')
    def test_fetch_linear_failure(self, mock_fetch):
        """Test failed Linear data fetch."""
        mock_fetch.side_effect = Exception('API Error')
        context = mb.DailyContext()
        context.linear_api_key = 'test_key'
        context.fetch_linear()
        self.assertIsNone(context.linear_data)

    @patch('scripts.morning_brief.morning_brief.fetch_github_notes')
    def test_fetch_github_notes_success(self, mock_fetch):
        """Test successful GitHub notes fetch."""
        mock_fetch.return_value = ['note1', 'note2']
        context = mb.DailyContext()
        context.github_token = 'test_token'
        context.fetch_github_notes()
        self.assertEqual(context.github_notes, ['note1', 'note2'])

    @patch('scripts.morning_brief.morning_brief.fetch_github_notes')
    def test_fetch_github_notes_failure(self, mock_fetch):
        """Test failed GitHub notes fetch."""
        mock_fetch.side_effect = Exception('API Error')
        context = mb.DailyContext()
        context.github_token = 'test_token'
        context.fetch_github_notes()
        self.assertIsNone(context.github_notes)

    def test_daily_context_build(self):
        ctx = mb.DailyContext.build("-05:00")
        assert ctx.today == dt.date.today()

    def test_section_toggles_initialization(self):
        """Test SectionToggles initialization."""
        toggles = mb.SectionToggles()
        self.assertTrue(toggles.weather)
        self.assertTrue(toggles.podcast)
        self.assertTrue(toggles.linear)
        self.assertTrue(toggles.github)
        self.assertTrue(toggles.horoscope)

    def test_section_toggles_from_env(self):
        """Test SectionToggles initialization from environment variables."""
        os.environ['DISABLE_WEATHER'] = 'true'
        os.environ['DISABLE_PODCAST'] = 'true'
        toggles = mb.SectionToggles()
        self.assertFalse(toggles.weather)
        self.assertFalse(toggles.podcast)
        self.assertTrue(toggles.linear)
        self.assertTrue(toggles.github)
        self.assertTrue(toggles.horoscope)
        del os.environ['DISABLE_WEATHER']
        del os.environ['DISABLE_PODCAST']

    def test_section_toggles_all_enabled(self):
        t = mb.SectionToggles()
        assert t.any_enabled is True

    def test_section_toggles_all_disabled(self):
        t = mb.SectionToggles(greeting=False, focus=False, news=False, podcast=False)
        assert t.any_enabled is False

    def test_section_toggles_partial(self):
        t = mb.SectionToggles(greeting=False, focus=False, news=True, podcast=False)
        assert t.any_enabled is True

    def test_process_podcast_feed_empty(self):
        llm_mock = Mock()
        session_mock = Mock()
        entries = []

        result = mb._process_podcast_feed(entries, llm_mock, session_mock, 3)
        assert result.tags == []
        assert "America Adapts" in result.html

    def test_process_podcast_feed_success(self):
        llm_mock = Mock()
        llm_mock.summarize_podcast.return_value = (
            "AI summary for testing coastal systems."
        )
        session_mock = Mock()

        entries = [
            {
                "title": "Episode 1",
                "link": "http://example.com/1",
                "published": "Mon, 01 Jan 2026",
                "summary": "Original summary",
            }
        ]

        result = mb._process_podcast_feed(entries, llm_mock, session_mock, 3)

        assert "AI summary for testing coastal systems" in result.html
        assert "Episode 1" in result.html
        assert "coastal-science" in result.tags

    def test_fetch_weather_cache_hit(self):
        config = Mock()
        config.lat = 40.7128
        config.lon = -74.0060
        config.weather_cache_ttl = 3600
        cache = Mock()
        session = Mock()

        cache.get.return_value = {
            "current_temp": "65.5",
            "high_temp": "72.1",
            "rain_probability": "15",
            "narrative": "Cached narrative.",
        }

        result = mb.fetch_weather(session, config, cache)

        assert result.current_temp == "65.5"
        assert result.high_temp == "72.1"
        assert result.rain_probability == "15"
        assert result.narrative == "Cached narrative."
        session.get.assert_not_called()

    def test_fetch_weather_success(self):
        config = Mock()
        config.lat = 40.7128
        config.lon = -74.0060
        config.weather_cache_ttl = 3600
        cache = Mock()
        session = Mock()

        cache.get.return_value = None

        response = Mock()
        response.json.return_value = {
            "current_weather": {"temperature": 65.5},
            "daily": {
                "temperature_2m_max": [72.1],
                "precipitation_probability_max": [15],
            },
        }
        session.get.return_value = response

        result = mb.fetch_weather(session, config, cache)

        assert result.current_temp == "65.5"
        assert result.high_temp == "72.1"
        assert result.rain_probability == "15"
        assert "65.5F" in result.narrative

        cache.set.assert_called_once()

    def test_fetch_weather_timeout(self):
        config = Mock()
        config.lat = 40.7128
        config.lon = -74.0060
        config.weather_cache_ttl = 3600
        cache = Mock()
        session = Mock()

        cache.get.return_value = None
        session.get.side_effect = Exception("Connection timed out")

        result = mb.fetch_weather(session, config, cache)

        assert result.current_temp == "N/A"
        assert result.high_temp == "N/A"
        assert result.rain_probability == "N/A"
        assert result.narrative == "Weather data unavailable."

    def test_fetch_weather_http_error(self):
        config = Mock()
        config.lat = 40.7128
        config.lon = -74.0060
        config.weather_cache_ttl = 3600
        cache = Mock()
        session = Mock()

        cache.get.return_value = None

        response = Mock()
        response.raise_for_status.side_effect = Exception("404 Client Error")
        session.get.return_value = response

        result = mb.fetch_weather(session, config, cache)

        assert result.current_temp == "N/A"
        assert result.high_temp == "N/A"
        assert result.rain_probability == "N/A"
        assert result.narrative == "Weather data unavailable."