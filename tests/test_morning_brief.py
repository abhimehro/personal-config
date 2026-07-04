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


# ============================================================
# Text Helpers
# ============================================================


class TestSanitizeText(unittest.TestCase):
    def test_none(self):
        assert mb.sanitize_text(None) == ""

    def test_plain(self):
        assert mb.sanitize_text("hello") == "hello"

    def test_html_entities(self):
        assert mb.sanitize_text('<script>alert("xss")</script>') == (
            "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;"
        )

    def test_strips_whitespace(self):
        assert mb.sanitize_text("  padded  ") == "padded"

    def test_numeric_input(self):
        assert mb.sanitize_text(42) == "42"

    def test_ampersand(self):
        assert mb.sanitize_text("A & B") == "A &amp; B"


class TestTruncateText(unittest.TestCase):
    def test_short_text_unchanged(self):
        assert mb.truncate_text("short", 100) == "short"

    def test_exact_length(self):
        text = "a" * 150
        assert mb.truncate_text(text, 150) == text

    def test_long_text_truncated(self):
        text = "a" * 200
        result = mb.truncate_text(text, 150)
        assert result.endswith("...")
        assert len(result) == 150

    def test_empty(self):
        assert mb.truncate_text("", 10) == ""

    def test_none(self):
        assert mb.truncate_text(None, 10) == ""


class TestStripHtmlTags(unittest.TestCase):
    def test_removes_tags(self):
        assert mb.strip_html_tags("<p>Hello <b>world</b></p>") == "Hello world"

    def test_empty(self):
        assert mb.strip_html_tags("") == ""

    def test_no_tags(self):
        assert mb.strip_html_tags("plain text") == "plain text"

    def test_nested_tags(self):
        assert mb.strip_html_tags("<div><p><span>deep</span></p></div>") == "deep"


# ============================================================
# HTML Helpers
# ============================================================


class TestHtmlHelpers(unittest.TestCase):
    def test_html_li(self):
        assert mb.html_li("content") == "<li>content</li>"

    def test_html_ul(self):
        items = ["<li>a</li>", "<li>b</li>"]
        assert mb.html_ul(items) == "<ul><li>a</li><li>b</li></ul>"

    def test_html_section(self):
        result = mb.html_section("Title", "<p>body</p>")
        assert "<h3>Title</h3>" in result
        assert "<p>body</p>" in result

    def test_html_section_escapes_title(self):
        result = mb.html_section("<script>", "<p>safe</p>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_html_section_with_emoji(self):
        result = mb.html_section("🌅 Good Morning", "<p>body</p>")
        assert "aria-label" not in result
        assert '<span aria-hidden="true">🌅</span>' in result
        assert "Good Morning</h3>" in result

    def test_html_section_non_ascii_text(self):
        result = mb.html_section("Café Menu", "<p>body</p>")
        assert "aria-label" not in result
        assert '<span aria-hidden="true">' not in result
        assert "<h3>Café Menu</h3>" in result


# ============================================================
# Date Helpers
# ============================================================


class TestIsDueToday(unittest.TestCase):
    def test_matches(self):
        assert mb.is_due_today("2026-03-25", "2026-03-25") is True

    def test_no_match(self):
        assert mb.is_due_today("2026-03-26", "2026-03-25") is False

    def test_empty(self):
        assert mb.is_due_today("", "2026-03-25") is False

    def test_none_like(self):
        assert mb.is_due_today(None, "2026-03-25") is False


# ============================================================
# Horoscope Extraction
# ============================================================


class TestExtractHoroscopeText(unittest.TestCase):
    def test_nested_data(self):
        payload = {"data": {"horoscope_data": "Stars align."}}
        assert mb.extract_horoscope_text(payload) == "Stars align."

    def test_flat_horoscope(self):
        assert mb.extract_horoscope_text({"horoscope": "Be bold."}) == "Be bold."

    def test_description_fallback(self):
        assert (
            mb.extract_horoscope_text({"description": "Trust yourself."})
            == "Trust yourself."
        )

    def test_empty_dict(self):
        assert mb.extract_horoscope_text({}) is None

    def test_non_dict(self):
        assert mb.extract_horoscope_text("not a dict") is None

    def test_whitespace_only(self):
        assert mb.extract_horoscope_text({"horoscope": "   "}) is None

    def test_flat_horoscope_data(self):
        assert (
            mb.extract_horoscope_text({"horoscope_data": "Flat data."}) == "Flat data."
        )

    def test_priority_order(self):
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

    def test_non_string_candidates(self):
        payload = {
            "horoscope_data": 123,
            "horoscope": ["not", "a", "string"],
            "description": "The only string.",
        }
        assert mb.extract_horoscope_text(payload) == "The only string."

    def test_nested_not_dict(self):
        # If 'data' is a string, it shouldn't crash nested.get
        payload = {"data": "not-a-dict", "horoscope": "Fallback."}
        assert mb.extract_horoscope_text(payload) == "Fallback."


# ============================================================
# Staleness Calculation
# ============================================================


class TestStaleness(unittest.TestCase):
    TODAY = dt.date(2026, 3, 25)

    def test_zero_for_today(self):
        assert mb.staleness_days("2026-03-25T12:00:00Z", self.TODAY) == 0

    def test_positive_days(self):
        assert mb.staleness_days("2026-03-20T12:00:00Z", self.TODAY) == 5

    def test_empty_string(self):
        assert mb.staleness_days("", self.TODAY) == 0

    def test_invalid_format(self):
        assert mb.staleness_days("not-a-date", self.TODAY) == 0

    def test_future_date(self):
        assert mb.staleness_days("2026-03-30T12:00:00Z", self.TODAY) == 0


# ============================================================
# Linear Issue Scoring
# ============================================================


class TestScoreLinearIssue(unittest.TestCase):
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


# ============================================================
# Calendar Admin Scoring
# ============================================================


# ============================================================
# Focus Meta / Selection
# ============================================================


class TestBuildFocusMetaParts(unittest.TestCase):
    def test_full_item(self):
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

    def test_empty_item(self):
        item = mb.FocusItem(kind="linear", identifier="", title="", url="#")
        assert mb.build_focus_meta_parts(item, "2026-03-25") == []


class TestSelectFocusPair(unittest.TestCase):
    def test_both_available(self):
        li = [mb.FocusItem(kind="linear", identifier="A", title="t", url="#")]
        ci = [mb.FocusItem(kind="calendar", identifier="B", title="t", url="#")]
        deep, admin = mb.select_focus_pair(li, ci)
        assert deep is not None
        assert admin is not None

    def test_both_empty(self):
        deep, admin = mb.select_focus_pair([], [])
        assert deep is None
        assert admin is None


class TestBuildSelectionReason(unittest.TestCase):
    def test_no_item_deep(self):
        result = mb.build_selection_reason("deep work", None, "2026-03-25")
        assert "general planning" in result

    def test_no_item_admin(self):
        result = mb.build_selection_reason("admin", None, "2026-03-25")
        assert "housekeeping" in result

    def test_linear_due_today(self):
        item = mb.FocusItem(
            kind="linear", identifier="X", title="t", url="#", due_date="2026-03-25"
        )
        result = mb.build_selection_reason("deep work", item, "2026-03-25")
        assert "due today" in result

    def test_calendar_item(self):
        item = mb.FocusItem(
            kind="calendar", identifier="C", title="t", url="#", time_label="09:00"
        )
        result = mb.build_selection_reason("admin", item, "2026-03-25")
        assert "time block" in result


# ============================================================
# Dynamic Tag Inference
# ============================================================


class TestDeriveDynamicTags(unittest.TestCase):
    def test_coastal_keyword(self):
        assert "coastal-science" in mb.derive_dynamic_tags(
            "The coastal wetland study results"
        )

    def test_no_match(self):
        assert mb.derive_dynamic_tags("Regular news about nothing relevant") == []

    def test_empty(self):
        assert mb.derive_dynamic_tags("") == []


# ============================================================
# Time-aware Guidance
# ============================================================


class TestTimeAwareGuidance(unittest.TestCase):
    def test_morning(self):
        result = mb.get_time_aware_guidance(dt.datetime(2026, 3, 25, 8, 0))
        assert "deep work" in result.lower()

    def test_midday(self):
        result = mb.get_time_aware_guidance(dt.datetime(2026, 3, 25, 13, 0))
        assert "handoff" in result.lower()

    def test_evening(self):
        result = mb.get_time_aware_guidance(dt.datetime(2026, 3, 25, 18, 0))
        assert "lighter" in result.lower()


# ============================================================
# GitHub Context Note
# ============================================================


class TestGithubContextNote(unittest.TestCase):
    def test_linear_deep(self):
        item = mb.FocusItem(kind="linear", identifier="X", title="t", url="#")
        result = mb.build_github_context_note(item, None)
        assert "admin block" in result

    def test_calendar_admin(self):
        item = mb.FocusItem(kind="calendar", identifier="C", title="t", url="#")
        result = mb.build_github_context_note(None, item)
        assert "GitHub sweep" in result

    def test_fallback(self):
        result = mb.build_github_context_note(None, None)
        assert "admin slot" in result


# ============================================================
# Environment Helpers
# ============================================================


class TestEnvBool(unittest.TestCase):
    def test_defaults_true(self):
        assert mb._env_bool("NONEXISTENT_KEY_XYZ_123", True) is True

    def test_defaults_false(self):
        assert mb._env_bool("NONEXISTENT_KEY_XYZ_123", False) is False

    def test_empty_string(self):
        os.environ["_TEST_BOOL"] = ""
        assert mb._env_bool("_TEST_BOOL", True) is True
        assert mb._env_bool("_TEST_BOOL", False) is False
        del os.environ["_TEST_BOOL"]

    def test_whitespace_string(self):
        os.environ["_TEST_BOOL"] = "   "
        assert mb._env_bool("_TEST_BOOL", True) is True
        assert mb._env_bool("_TEST_BOOL", False) is False
        del os.environ["_TEST_BOOL"]

    def test_unrecognized_value(self):
        os.environ["_TEST_BOOL"] = "unknown"
        # Anything not explicitly false is true.
        assert mb._env_bool("_TEST_BOOL", False) is True
        del os.environ["_TEST_BOOL"]

    def test_false_values(self):
        for val in ("0", "false", "no", "off", "disabled"):
            os.environ["_TEST_BOOL"] = val
            assert mb._env_bool("_TEST_BOOL", True) is False
            del os.environ["_TEST_BOOL"]

    def test_true_values(self):
        for val in ("1", "true", "yes", "on"):
            os.environ["_TEST_BOOL"] = val
            assert mb._env_bool("_TEST_BOOL", False) is True
            del os.environ["_TEST_BOOL"]


class TestSafeInt(unittest.TestCase):
    def test_valid(self):
        os.environ["_TEST_INT"] = "42"
        assert mb._safe_int("_TEST_INT", 10) == 42
        del os.environ["_TEST_INT"]

    def test_negative(self):
        os.environ["_TEST_INT"] = "-42"
        assert mb._safe_int("_TEST_INT", 10) == -42
        del os.environ["_TEST_INT"]

    def test_padded_int(self):
        os.environ["_TEST_INT"] = "  42  "
        assert mb._safe_int("_TEST_INT", 10) == 42
        del os.environ["_TEST_INT"]

    def test_empty_string(self):
        os.environ["_TEST_INT"] = ""
        assert mb._safe_int("_TEST_INT", 10) == 10
        del os.environ["_TEST_INT"]

    def test_whitespace_string(self):
        os.environ["_TEST_INT"] = "   "
        assert mb._safe_int("_TEST_INT", 10) == 10
        del os.environ["_TEST_INT"]

    def test_float_fallback(self):
        os.environ["_TEST_INT"] = "3.14"
        assert mb._safe_int("_TEST_INT", 10) == 10
        del os.environ["_TEST_INT"]

    def test_invalid(self):
        os.environ["_TEST_INT"] = "abc"
        assert mb._safe_int("_TEST_INT", 10) == 10
        del os.environ["_TEST_INT"]

    def test_missing(self):
        assert mb._safe_int("_MISSING_KEY_123", 5) == 5


# ============================================================
# Cache
# ============================================================


class TestFileCache(unittest.TestCase):
    def test_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cache = mb.FileCache(str(Path(td) / "cache"))
            cache.set("test-key", {"hello": "world"})
            result = cache.get("test-key", ttl=60)
            self.assertEqual(result, {"hello": "world"})

    def test_expired(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cache = mb.FileCache(str(Path(td) / "cache"))
            cache.set("test-key", "value")
            result = cache.get("test-key", ttl=0)
            self.assertIsNone(result)

    def test_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cache = mb.FileCache(str(Path(td) / "cache"))
            self.assertIsNone(cache.get("nonexistent", ttl=60))

    def test_corrupted_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cache = mb.FileCache(str(Path(td) / "cache"))
            cache.set("test-key", "value")
            path = cache._key_path("test-key")
            path.write_text("NOT VALID JSON", encoding="utf-8")
            self.assertIsNone(cache.get("test-key", ttl=60))

    def test_string_value(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cache = mb.FileCache(str(Path(td) / "cache"))
            cache.set("html", "<h1>Hello</h1>")
            self.assertEqual(cache.get("html", ttl=60), "<h1>Hello</h1>")


# ============================================================
# DailyContext
# ============================================================


class TestDailyContext(unittest.TestCase):
    def test_build(self):
        ctx = mb.DailyContext.build("-05:00")
        assert ctx.today == dt.date.today()


# ============================================================
# SectionToggles
# ============================================================


class TestSectionToggles(unittest.TestCase):
    def test_all_enabled(self):
        t = mb.SectionToggles()
        assert t.any_enabled is True

    def test_all_disabled(self):
        t = mb.SectionToggles(greeting=False, focus=False, news=False, podcast=False)
        assert t.any_enabled is False

    def test_partial(self):
        t = mb.SectionToggles(greeting=False, focus=False, news=True, podcast=False)
        assert t.any_enabled is True


# ============================================================
# Weather
# ============================================================


class TestFetchWeather(unittest.TestCase):
    def setUp(self):
        from unittest.mock import Mock

        self.config = Mock()
        self.config.lat = 40.7128
        self.config.lon = -74.0060
        self.config.weather_cache_ttl = 3600
        self.cache = Mock()
        self.session = Mock()

    def test_cache_hit(self):
        self.cache.get.return_value = {
            "current_temp": "65.5",
            "high_temp": "72.1",
            "rain_probability": "15",
            "narrative": "Cached narrative."
        }

        result = mb.fetch_weather(self.session, self.config, self.cache)

        assert result.current_temp == "65.5"
        assert result.high_temp == "72.1"
        assert result.rain_probability == "15"
        assert result.narrative == "Cached narrative."
        self.session.get.assert_not_called()

    def test_fetch_success(self):
        from unittest.mock import Mock

        self.cache.get.return_value = None

        response = Mock()
        response.json.return_value = {
            "current_weather": {"temperature": 65.5},
            "daily": {
                "temperature_2m_max": [72.1],
                "precipitation_probability_max": [15]
            }
        }
        self.session.get.return_value = response

        result = mb.fetch_weather(self.session, self.config, self.cache)

        assert result.current_temp == "65.5"
        assert result.high_temp == "72.1"
        assert result.rain_probability == "15"
        assert "65.5F" in result.narrative

        self.cache.set.assert_called_once()

    def test_fetch_timeout(self):
        self.cache.get.return_value = None
        self.session.get.side_effect = Exception("Connection timed out")

        result = mb.fetch_weather(self.session, self.config, self.cache)

        assert result.current_temp == "N/A"
        assert result.high_temp == "N/A"
        assert result.rain_probability == "N/A"
        assert result.narrative == "Weather data unavailable."

    def test_fetch_http_error(self):
        from unittest.mock import Mock

        self.cache.get.return_value = None

        response = Mock()
        response.raise_for_status.side_effect = Exception("404 Client Error")
        self.session.get.return_value = response

        result = mb.fetch_weather(self.session, self.config, self.cache)

        assert result.current_temp == "N/A"
        assert result.high_temp == "N/A"
        assert result.rain_probability == "N/A"
        assert result.narrative == "Weather data unavailable."
