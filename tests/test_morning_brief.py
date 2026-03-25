#!/usr/bin/env python3
"""
Unit tests for the pure helpers in morning-brief.py.

Run with:
    python3 -m pytest test_morning_brief.py -v
"""

from __future__ import annotations

import datetime as dt

# Adjust import path if needed (e.g., if script is in scripts/morning-brief/)
# sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util
import os
import sys as _sys
from pathlib import Path

import pytest

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


class TestSanitizeText:
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


class TestTruncateText:
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


class TestStripHtmlTags:
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


class TestHtmlHelpers:
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


# ============================================================
# Date Helpers
# ============================================================


class TestIsDueToday:
    def test_matches(self):
        assert mb.is_due_today("2026-03-25", "2026-03-25") is True

    def test_no_match(self):
        assert mb.is_due_today("2026-03-26", "2026-03-25") is False

    def test_empty(self):
        assert mb.is_due_today("", "2026-03-25") is False

    def test_none_like(self):
        assert mb.is_due_today(None, "2026-03-25") is False


class TestFormatTimeLabel:
    def test_datetime(self):
        assert mb.format_time_label("2026-03-25T09:30:00-05:00") == "09:30"

    def test_date_only(self):
        assert mb.format_time_label("2026-03-25") == "All day"

    def test_empty(self):
        assert mb.format_time_label("") == "Anytime"


# ============================================================
# Horoscope Extraction
# ============================================================


class TestExtractHoroscopeText:
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


# ============================================================
# Staleness Calculation
# ============================================================


class TestStaleness:
    def test_zero_for_today(self):
        assert mb.staleness_days("2026-03-25T12:00:00Z", "2026-03-25") == 0

    def test_positive_days(self):
        assert mb.staleness_days("2026-03-20T12:00:00Z", "2026-03-25") == 5

    def test_empty_string(self):
        assert mb.staleness_days("", "2026-03-25") == 0

    def test_invalid_format(self):
        assert mb.staleness_days("not-a-date", "2026-03-25") == 0

    def test_future_date(self):
        assert mb.staleness_days("2026-03-30T12:00:00Z", "2026-03-25") == 0


# ============================================================
# Linear Issue Scoring
# ============================================================


class TestScoreLinearIssue:
    TODAY = "2026-03-25"

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
        issue = self._issue(priority=1, dueDate=self.TODAY)
        score = mb.score_linear_issue(issue, self.TODAY)
        assert score >= 180  # 100 + 80 + state

    def test_no_priority_no_due(self):
        issue = self._issue()
        score = mb.score_linear_issue(issue, self.TODAY)
        assert score >= 0
        assert score < 50

    def test_started_state_bonus(self):
        issue = self._issue(state={"name": "In Progress", "type": "started"})
        score_started = mb.score_linear_issue(issue, self.TODAY)
        issue_backlog = self._issue(state={"name": "Backlog", "type": "backlog"})
        score_backlog = mb.score_linear_issue(issue_backlog, self.TODAY)
        assert score_started > score_backlog

    def test_label_bonus(self):
        issue_bug = self._issue(labels={"nodes": [{"name": "Bug"}]})
        issue_plain = self._issue()
        assert mb.score_linear_issue(issue_bug, self.TODAY) > mb.score_linear_issue(
            issue_plain, self.TODAY
        )

    def test_staleness_penalty(self):
        issue_stale = self._issue(updatedAt="2026-02-01T00:00:00Z")
        issue_fresh = self._issue(updatedAt="2026-03-24T00:00:00Z")
        assert mb.score_linear_issue(issue_fresh, self.TODAY) >= mb.score_linear_issue(
            issue_stale, self.TODAY
        )

    def test_cycle_bonus(self):
        issue_cycle = self._issue(cycle={"id": "abc"})
        issue_no_cycle = self._issue()
        assert mb.score_linear_issue(issue_cycle, self.TODAY) > mb.score_linear_issue(
            issue_no_cycle, self.TODAY
        )

    def test_score_never_negative(self):
        issue = self._issue(updatedAt="2020-01-01T00:00:00Z")
        assert mb.score_linear_issue(issue, self.TODAY) >= 0

    def test_missing_fields(self):
        """Issues with completely missing fields should not crash."""
        score = mb.score_linear_issue({}, self.TODAY)
        assert isinstance(score, int)
        assert score >= 0


# ============================================================
# Calendar Admin Scoring
# ============================================================


class TestCalendarAdminScore:
    def test_strong_keywords(self):
        assert mb.calendar_admin_score("System Maintenance") > 0

    def test_no_keywords(self):
        assert mb.calendar_admin_score("Coffee with Sarah") == 0

    def test_description_included(self):
        assert mb.calendar_admin_score("Meeting", "health check on servers") > 0

    def test_multiple_keywords(self):
        score = mb.calendar_admin_score("Admin Review and Cleanup")
        assert score >= 14  # admin(4) + review(4) + cleanup(6)


# ============================================================
# Focus Meta / Selection
# ============================================================


class TestBuildFocusMetaParts:
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


class TestSelectFocusPair:
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


class TestBuildSelectionReason:
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


class TestDeriveDynamicTags:
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


class TestTimeAwareGuidance:
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


class TestGithubContextNote:
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


class TestEnvBool:
    def test_defaults_true(self):
        assert mb._env_bool("NONEXISTENT_KEY_XYZ_123", True) is True

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


class TestSafeInt:
    def test_valid(self):
        os.environ["_TEST_INT"] = "42"
        assert mb._safe_int("_TEST_INT", 10) == 42
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


class TestFileCache:
    def test_roundtrip(self, tmp_path):
        cache = mb.FileCache(str(tmp_path / "cache"))
        cache.set("test-key", {"hello": "world"})
        result = cache.get("test-key", ttl=60)
        assert result == {"hello": "world"}

    def test_expired(self, tmp_path):
        cache = mb.FileCache(str(tmp_path / "cache"))
        cache.set("test-key", "value")
        result = cache.get("test-key", ttl=0)
        assert result is None

    def test_missing(self, tmp_path):
        cache = mb.FileCache(str(tmp_path / "cache"))
        assert cache.get("nonexistent", ttl=60) is None

    def test_corrupted_json(self, tmp_path):
        cache = mb.FileCache(str(tmp_path / "cache"))
        cache.set("test-key", "value")
        path = cache._key_path("test-key")
        path.write_text("NOT VALID JSON", encoding="utf-8")
        assert cache.get("test-key", ttl=60) is None

    def test_string_value(self, tmp_path):
        cache = mb.FileCache(str(tmp_path / "cache"))
        cache.set("html", "<h1>Hello</h1>")
        assert cache.get("html", ttl=60) == "<h1>Hello</h1>"


# ============================================================
# DailyContext
# ============================================================


class TestDailyContext:
    def test_build(self):
        ctx = mb.DailyContext.build("-05:00")
        assert ctx.today == dt.date.today()
        assert "-05:00" in ctx.calendar_time_min
        assert "-05:00" in ctx.calendar_time_max


# ============================================================
# SectionToggles
# ============================================================


class TestSectionToggles:
    def test_all_enabled(self):
        t = mb.SectionToggles()
        assert t.any_enabled is True

    def test_all_disabled(self):
        t = mb.SectionToggles(greeting=False, focus=False, news=False, podcast=False)
        assert t.any_enabled is False

    def test_partial(self):
        t = mb.SectionToggles(greeting=False, focus=False, news=True, podcast=False)
        assert t.any_enabled is True
