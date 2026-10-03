"""Unit and integration tests for Agent-Native PR Recap CLI.

Covers:
- Issue identifier extraction (branch, commit, title, body)
- Relationship mapping (closes, contributes, links) and deterministic precedence
- Normalization, deduplication, case insensitivity, malformed keys
- State transitions, non-regression guards, merge/close handling, idempotency
- Anchored recap comment creation, update, and unrelated comment preservation
- PR diff backlink attachment and duplicate prevention
- GitNexus output parsing, degraded handling, and fallback formatting
- Configuration loading, validation, and error reporting
- CLI execution, GitHub Actions event mapping, and safe no-op handling
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure scripts dir is on sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pr_recap  # noqa: E402
from pr_recap import (  # noqa: E402
    CANONICAL_STATES,
    DEFAULT_COMMENT_ANCHOR,
    Config,
    GitNexusAnalysis,
    GitNexusAnalyzer,
    LinearApiError,
    LinearClient,
    LinearIssue,
    LinearState,
    PRContext,
    build_recap_comment,
    compute_state_transition,
    extract_github_issue_references,
    extract_issue_keys,
    load_config,
    run_sync,
)


class TestIssueExtraction(unittest.TestCase):
    """Test issue key extraction, normalization, and relationship precedence."""

    def test_branch_extraction(self) -> None:
        test_cases = [
            ("feature/PROJ-123", {"PROJ-123": "links"}),
            ("fix/ABHI-456-security-patch", {"ABHI-456": "links"}),
            ("chore/ENG-789/cleanup-code", {"ENG-789": "links"}),
            ("FEATURE/lower-100", {"LOWER-100": "links"}),
            ("feature/proj-123-my-desc", {"PROJ-123": "links"}),
        ]
        for branch, expected in test_cases:
            with self.subTest(branch=branch):
                result = extract_issue_keys(branch_name=branch)
                self.assertEqual(result, expected)

    def test_branch_non_matching(self) -> None:
        non_matching = [
            "main",
            "master",
            "develop",
            "release/v1.0",
            "custom-branch-name",
            "fix/no_key",
        ]
        for branch in non_matching:
            with self.subTest(branch=branch):
                result = extract_issue_keys(branch_name=branch)
                self.assertEqual(result, {})

    def test_commit_message_relationships(self) -> None:
        commits = (
            "Fixes ABHI-101 and Closes PROJ-102",
            "Contributes to ENG-103: partial implementation",
            "Relates to DOC-104 for architecture notes",
            "Random commit mentioning ABC-105 in message",
        )
        result = extract_issue_keys(commit_messages=commits)
        self.assertEqual(result.get("ABHI-101"), "closes")
        self.assertEqual(result.get("PROJ-102"), "closes")
        self.assertEqual(result.get("ENG-103"), "contributes")
        self.assertEqual(result.get("DOC-104"), "links")
        self.assertEqual(result.get("ABC-105"), "links")

    def test_case_insensitivity_in_commit_keywords(self) -> None:
        commits = (
            "fixes abhi-201",
            "CLOSES proj-202",
            "contributes to eng-203",
            "relates to doc-204",
        )
        result = extract_issue_keys(commit_messages=commits)
        self.assertEqual(result.get("ABHI-201"), "closes")
        self.assertEqual(result.get("PROJ-202"), "closes")
        self.assertEqual(result.get("ENG-203"), "contributes")
        self.assertEqual(result.get("DOC-204"), "links")

    def test_pr_title_and_body_fallback(self) -> None:
        title = "feat: add user authentication (ABHI-301)"
        body = "This PR implements OAuth2 login.\nCloses ABHI-302\nContributes to ABHI-303\nSee also ABHI-304."
        result = extract_issue_keys(pr_title=title, pr_body=body)
        self.assertEqual(result.get("ABHI-301"), "links")
        self.assertEqual(result.get("ABHI-302"), "closes")
        self.assertEqual(result.get("ABHI-303"), "contributes")
        self.assertEqual(result.get("ABHI-304"), "links")

    def test_deterministic_precedence(self) -> None:
        # Same issue key across branch, title, body, and commits with different declarations
        # 'closes' > 'contributes' > 'links'
        result = extract_issue_keys(
            branch_name="feature/CORE-999-auth",  # links
            pr_title="CORE-999: update login flow",  # links
            pr_body="Contributes to CORE-999",  # contributes
            commit_messages=("Fixes CORE-999",),  # closes
        )
        self.assertEqual(result.get("CORE-999"), "closes")

        # 'contributes' over 'links'
        result2 = extract_issue_keys(
            branch_name="feature/CORE-888-billing",  # links
            pr_title="CORE-888: billing setup",  # links
            pr_body="Contributes to CORE-888",  # contributes
        )
        self.assertEqual(result2.get("CORE-888"), "contributes")

    def test_malformed_keys_ignored(self) -> None:
        commits = (
            "Fixes ABHI- without number",
            "-123 missing letters",
            "123-ABHI invalid prefix",
            "A-1 single letter prefix",
            "VERYLONGLONGIDENTIFIER-123 too long prefix",
        )
        result = extract_issue_keys(commit_messages=commits)
        self.assertEqual(result, {})

    def test_normalization_and_deduplication(self) -> None:
        commits = (
            "Fixes abhi-123",
            "Closes ABHI-123",
            "Relates to AbHi-123",
        )
        result = extract_issue_keys(commit_messages=commits)
        self.assertEqual(len(result), 1)
        self.assertIn("ABHI-123", result)
        self.assertEqual(result["ABHI-123"], "closes")

    def test_version_numbers_not_extracted(self) -> None:
        commits = (
            "fix(media): support pre-3.12 directory listings (#2278)",
            "bump version to v2-1.0 release",
            "upgrade to python-3.11",
            "PRE-3.12 should not match as issue",
        )
        result = extract_issue_keys(commit_messages=commits)
        self.assertEqual(result, {})

    def test_explicit_issues_extraction(self) -> None:
        result = extract_issue_keys(
            branch_name="main",
            explicit_issues=["ABHI-901", "ABHI-902:closes", "ABHI-903:contributes"],
        )
        self.assertEqual(result.get("ABHI-901"), "links")
        self.assertEqual(result.get("ABHI-902"), "closes")
        self.assertEqual(result.get("ABHI-903"), "contributes")

    def test_expanded_branch_categories(self) -> None:
        test_cases = [
            ("sentinel/ABHI-500", {"ABHI-500": "links"}),
            ("palette/ABHI-600-color-fix", {"ABHI-600": "links"}),
            ("bolt/ABHI-700/perf", {"ABHI-700": "links"}),
            ("devin/ABHI-800", {"ABHI-800": "links"}),
            ("cursor-agent/ABHI-900", {"ABHI-900": "links"}),
            ("ABHI-950-standalone-issue-branch", {"ABHI-950": "links"}),
        ]
        for branch, expected in test_cases:
            with self.subTest(branch=branch):
                result = extract_issue_keys(branch_name=branch)
                self.assertEqual(result, expected)

    def test_github_issue_references_extraction(self) -> None:
        refs = extract_github_issue_references(
            commit_messages=("Fixes #535: critical patch", "Contributes to #536"),
            pr_title="feat: add new feature (#537)",
            pr_body="Closes #538 and relates to #539",
        )
        self.assertEqual(refs.get("535"), "closes")
        self.assertEqual(refs.get("536"), "contributes")
        self.assertEqual(refs.get("537"), "links")
        self.assertEqual(refs.get("538"), "closes")
        self.assertEqual(refs.get("539"), "links")


class TestStateTransitions(unittest.TestCase):
    """Test Linear lifecycle state transitions and non-regression guards."""

    def setUp(self) -> None:
        self.state_map = dict(CANONICAL_STATES)

    def _make_state(
        self, state_name: str, state_type: str, state_id: str
    ) -> LinearState:
        return LinearState(id=state_id, name=state_name, type=state_type)

    def test_push_advances_from_backlog_or_todo(self) -> None:
        todo_state = self._make_state("Todo", "unstarted", self.state_map["todo"])
        backlog_state = self._make_state("Backlog", "backlog", "backlog-id")
        in_prog_state = self._make_state(
            "In Progress", "started", self.state_map["inProgress"]
        )
        in_rev_state = self._make_state(
            "In Review", "started", self.state_map["inReview"]
        )
        done_state = self._make_state("Done", "completed", self.state_map["done"])

        ctx = PRContext(
            event_name="push",
            action="opened",
            pr_number=None,
            pr_title="",
            pr_body="",
            pr_url="",
            branch_name="feature/PROJ-1",
            head_sha="sha",
            is_draft=False,
            is_merged=False,
            is_closed=False,
            commit_messages=(),
        )

        # Todo -> In Progress
        target, reason = compute_state_transition(
            todo_state, "links", ctx, self.state_map
        )
        self.assertEqual(target, self.state_map["inProgress"])

        # Backlog -> In Progress
        target, reason = compute_state_transition(
            backlog_state, "links", ctx, self.state_map
        )
        self.assertEqual(target, self.state_map["inProgress"])

        # Already In Progress -> No-op
        target, reason = compute_state_transition(
            in_prog_state, "links", ctx, self.state_map
        )
        self.assertIsNone(target)

        # In Review -> Non-regression guard blocks setting to In Progress
        target, reason = compute_state_transition(
            in_rev_state, "links", ctx, self.state_map
        )
        self.assertIsNone(target)

        # Done -> Non-regression guard blocks setting to In Progress
        target, reason = compute_state_transition(
            done_state, "links", ctx, self.state_map
        )
        self.assertIsNone(target)

    def test_draft_pr_opened(self) -> None:
        todo_state = self._make_state("Todo", "unstarted", self.state_map["todo"])
        in_rev_state = self._make_state(
            "In Review", "started", self.state_map["inReview"]
        )
        done_state = self._make_state("Done", "completed", self.state_map["done"])

        ctx = PRContext(
            event_name="pull_request",
            action="opened",
            pr_number=42,
            pr_title="Draft PR",
            pr_body="",
            pr_url="https://github.com/org/repo/pull/42",
            branch_name="feature/PROJ-1",
            head_sha="sha",
            is_draft=True,
            is_merged=False,
            is_closed=False,
            commit_messages=(),
        )

        # Todo -> In Progress
        target, reason = compute_state_transition(
            todo_state, "links", ctx, self.state_map
        )
        self.assertEqual(target, self.state_map["inProgress"])

        # In Review -> Do not regress!
        target, reason = compute_state_transition(
            in_rev_state, "links", ctx, self.state_map
        )
        self.assertIsNone(target)
        self.assertIn("non-regression guard", reason)

        # Done -> Do not regress!
        target, reason = compute_state_transition(
            done_state, "links", ctx, self.state_map
        )
        self.assertIsNone(target)

    def test_ready_for_review_advances_to_in_review(self) -> None:
        todo_state = self._make_state("Todo", "unstarted", self.state_map["todo"])
        in_prog_state = self._make_state(
            "In Progress", "started", self.state_map["inProgress"]
        )
        in_rev_state = self._make_state(
            "In Review", "started", self.state_map["inReview"]
        )
        done_state = self._make_state("Done", "completed", self.state_map["done"])

        ctx = PRContext(
            event_name="pull_request",
            action="ready_for_review",
            pr_number=42,
            pr_title="Ready PR",
            pr_body="",
            pr_url="https://github.com/org/repo/pull/42",
            branch_name="feature/PROJ-1",
            head_sha="sha",
            is_draft=False,
            is_merged=False,
            is_closed=False,
            commit_messages=(),
        )

        # Todo -> In Review
        target, _ = compute_state_transition(todo_state, "links", ctx, self.state_map)
        self.assertEqual(target, self.state_map["inReview"])

        # In Progress -> In Review
        target, _ = compute_state_transition(
            in_prog_state, "links", ctx, self.state_map
        )
        self.assertEqual(target, self.state_map["inReview"])

        # Already In Review -> No-op
        target, _ = compute_state_transition(in_rev_state, "links", ctx, self.state_map)
        self.assertIsNone(target)

        # Done -> Do not regress!
        target, reason = compute_state_transition(
            done_state, "links", ctx, self.state_map
        )
        self.assertIsNone(target)
        self.assertIn("refusing to regress", reason)

    def test_pr_merged_closes_only_on_closes(self) -> None:
        in_rev_state = self._make_state(
            "In Review", "started", self.state_map["inReview"]
        )
        done_state = self._make_state("Done", "completed", self.state_map["done"])

        ctx = PRContext(
            event_name="pull_request",
            action="closed",
            pr_number=42,
            pr_title="Merged PR",
            pr_body="",
            pr_url="https://github.com/org/repo/pull/42",
            branch_name="feature/PROJ-1",
            head_sha="sha",
            is_draft=False,
            is_merged=True,
            is_closed=True,
            commit_messages=(),
        )

        # relationship == 'closes' -> Done
        target, _ = compute_state_transition(
            in_rev_state, "closes", ctx, self.state_map
        )
        self.assertEqual(target, self.state_map["done"])

        # already Done -> No-op
        target, _ = compute_state_transition(done_state, "closes", ctx, self.state_map)
        self.assertIsNone(target)

        # relationship == 'contributes' -> NOT closed!
        target, reason = compute_state_transition(
            in_rev_state, "contributes", ctx, self.state_map
        )
        self.assertIsNone(target)
        self.assertIn("not 'closes'", reason)

        # relationship == 'links' -> NOT closed!
        target, reason = compute_state_transition(
            in_rev_state, "links", ctx, self.state_map
        )
        self.assertIsNone(target)
        self.assertIn("not 'closes'", reason)

    def test_pr_closed_without_merge(self) -> None:
        in_rev_state = self._make_state(
            "In Review", "started", self.state_map["inReview"]
        )
        done_state = self._make_state("Done", "completed", self.state_map["done"])

        ctx = PRContext(
            event_name="pull_request",
            action="closed",
            pr_number=42,
            pr_title="Abandoned PR",
            pr_body="",
            pr_url="https://github.com/org/repo/pull/42",
            branch_name="feature/PROJ-1",
            head_sha="sha",
            is_draft=False,
            is_merged=False,
            is_closed=True,
            commit_messages=(),
        )

        # From In Review -> Todo
        target, _ = compute_state_transition(
            in_rev_state, "closes", ctx, self.state_map
        )
        self.assertEqual(target, self.state_map["todo"])

        # From Done -> Do NOT regress
        target, reason = compute_state_transition(
            done_state, "closes", ctx, self.state_map
        )
        self.assertIsNone(target)
        self.assertIn("preserving", reason)


class TestRecapCommentAndDiffBacklink(unittest.TestCase):
    """Test anchored recap comment formatting, upserting, and diff backlink attachment."""

    def setUp(self) -> None:
        self.ctx = PRContext(
            event_name="pull_request",
            action="opened",
            pr_number=100,
            pr_title="Add biometric authentication",
            pr_body="Detailed PR description explaining the changes.",
            pr_url="https://github.com/owner/repo/pull/100",
            branch_name="feature/AUTH-100",
            head_sha="12345678",
            is_draft=False,
            is_merged=False,
            is_closed=False,
            commit_messages=("Commit 1: Setup biometric API",),
        )

    def test_recap_comment_format(self) -> None:
        analysis = GitNexusAnalysis(
            available=True,
            risk_level="MEDIUM",
            risk_score=45.0,
            direct_edits=("authenticateUser", "biometricHandler"),
            downstream_impact=("loginFlow", "authMiddleware"),
        )
        comment = build_recap_comment(self.ctx, analysis, DEFAULT_COMMENT_ANCHOR)

        # Anchor must be included
        self.assertIn(DEFAULT_COMMENT_ANCHOR, comment)
        self.assertIn("## 📋 PR Recap: #100: Add biometric authentication", comment)
        self.assertIn("https://github.com/owner/repo/pull/100", comment)
        self.assertIn("https://github.com/owner/repo/pull/100.diff", comment)
        self.assertIn("authenticateUser", comment)
        self.assertIn("loginFlow", comment)
        self.assertIn("MEDIUM (45%)", comment)

    def test_upsert_comment_creates_when_missing(self) -> None:
        client = LinearClient(api_key="test-key")
        client._execute_graphql = MagicMock(
            return_value={  # type: ignore
                "commentCreate": {"success": True, "comment": {"id": "c-1234"}}
            }
        )

        issue = LinearIssue(
            id="issue-uuid-1",
            identifier="AUTH-100",
            title="Biometrics",
            state=LinearState("s1", "In Review", "started"),
            comments=({"id": "c-unrelated", "body": "Great progress on this!"},),
            attachments=(),
        )

        comment_id, created = client.upsert_recap_comment(
            issue=issue,
            comment_body=f"{DEFAULT_COMMENT_ANCHOR}\nSummary content",
            anchor=DEFAULT_COMMENT_ANCHOR,
        )

        self.assertTrue(created)
        self.assertEqual(comment_id, "c-1234")
        client._execute_graphql.assert_called_once()
        mutation = client._execute_graphql.call_args[0][0]
        self.assertIn("commentCreate", mutation)

    def test_upsert_comment_updates_when_existing(self) -> None:
        client = LinearClient(api_key="test-key")
        client._execute_graphql = MagicMock(
            return_value={  # type: ignore
                "commentUpdate": {"success": True, "comment": {"id": "c-existing"}}
            }
        )

        issue = LinearIssue(
            id="issue-uuid-1",
            identifier="AUTH-100",
            title="Biometrics",
            state=LinearState("s1", "In Review", "started"),
            comments=(
                {"id": "c-unrelated", "body": "An unrelated comment"},
                {
                    "id": "c-existing",
                    "body": f"{DEFAULT_COMMENT_ANCHOR}\nOld recap content",
                },
            ),
            attachments=(),
        )

        comment_id, created = client.upsert_recap_comment(
            issue=issue,
            comment_body=f"{DEFAULT_COMMENT_ANCHOR}\nUpdated recap content",
            anchor=DEFAULT_COMMENT_ANCHOR,
        )

        self.assertFalse(created)
        self.assertEqual(comment_id, "c-existing")
        client._execute_graphql.assert_called_once()
        mutation, variables = client._execute_graphql.call_args[0]
        self.assertIn("commentUpdate", mutation)
        self.assertEqual(variables["id"], "c-existing")

    def test_ensure_diff_link_creates_when_missing(self) -> None:
        client = LinearClient(api_key="test-key")
        client._execute_graphql = MagicMock(
            return_value={  # type: ignore
                "attachmentCreate": {"success": True, "attachment": {"id": "att-1"}}
            }
        )

        issue = LinearIssue(
            id="issue-uuid-1",
            identifier="AUTH-100",
            title="Biometrics",
            state=LinearState("s1", "In Review", "started"),
            comments=(),
            attachments=(
                {
                    "id": "att-other",
                    "title": "Figma",
                    "url": "https://figma.com/file/123",
                },
            ),
        )

        diff_url = "https://github.com/owner/repo/pull/100.diff"
        created = client.ensure_diff_link(issue, diff_url, "PR #100 Diff")
        self.assertTrue(created)
        client._execute_graphql.assert_called_once()
        mutation, variables = client._execute_graphql.call_args[0]
        self.assertIn("attachmentCreate", mutation)
        self.assertEqual(variables["url"], diff_url)

    def test_ensure_diff_link_idempotent_when_present(self) -> None:
        client = LinearClient(api_key="test-key")
        client._execute_graphql = MagicMock()

        diff_url = "https://github.com/owner/repo/pull/100.diff"
        issue = LinearIssue(
            id="issue-uuid-1",
            identifier="AUTH-100",
            title="Biometrics",
            state=LinearState("s1", "In Review", "started"),
            comments=(),
            attachments=({"id": "att-diff", "title": "PR #100 Diff", "url": diff_url},),
        )

        created = client.ensure_diff_link(issue, diff_url, "PR #100 Diff")
        self.assertFalse(created)
        client._execute_graphql.assert_not_called()


class TestGitNexusIntegration(unittest.TestCase):
    """Test GitNexus output parsing, degraded read behavior, and missing data handling."""

    def test_parse_json_payload(self) -> None:
        analyzer = GitNexusAnalyzer()
        json_output = json.dumps(
            {
                "risk": "HIGH",
                "riskScore": 82.5,
                "changed": ["processPayment", "validateCard"],
                "affected": ["checkoutHandler", "webhookPipeline", "billingQueue"],
            }
        )
        result = analyzer._parse_output(json_output)
        self.assertTrue(result.available)
        self.assertEqual(result.risk_level, "HIGH")
        self.assertEqual(result.risk_score, 82.5)
        self.assertEqual(result.direct_edits, ("processPayment", "validateCard"))
        self.assertEqual(len(result.downstream_impact), 3)

    def test_parse_text_payload(self) -> None:
        analyzer = GitNexusAnalyzer()
        text_output = """
        → Changed: 5 symbols in 3 files
        → Affected: LoginFlow, TokenRefresh, APIMiddlewarePipeline
        → Risk: MEDIUM
        """
        result = analyzer._parse_output(text_output)
        self.assertTrue(result.available)
        self.assertEqual(result.risk_level, "MEDIUM")
        self.assertEqual(result.direct_edits, ("5 symbols in 3 files",))
        self.assertIn("LoginFlow", result.downstream_impact)
        self.assertIn("TokenRefresh", result.downstream_impact)

    def test_degraded_when_runner_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = GitNexusAnalyzer(workspace_root=Path(tmpdir))
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = ""
                result = analyzer.analyze()
                self.assertFalse(result.available)
                self.assertIn("GitNexus CLI not found", result.degraded_reason or "")
                markdown = result.render_markdown()
                self.assertIn("GitNexus blast-radius analysis degraded", markdown)


class TestConfigValidation(unittest.TestCase):
    """Test .pr-recap.json configuration loading and validation."""

    def test_valid_config_from_dict(self) -> None:
        cfg = Config.from_dict(
            {
                "teamId": "my-team",
                "stateMap": {
                    "inProgress": "custom-prog",
                    "inReview": "custom-rev",
                },
                "commentAnchor": "<!-- custom-anchor -->",
            }
        )
        self.assertEqual(cfg.team_id, "my-team")
        self.assertEqual(cfg.state_map["inProgress"], "custom-prog")
        self.assertEqual(cfg.state_map["done"], CANONICAL_STATES["done"])
        self.assertEqual(cfg.comment_anchor, "<!-- custom-anchor -->")

    def test_missing_team_id_raises_value_error(self) -> None:
        with self.assertRaises(ValueError) as cm:
            Config.from_dict({"stateMap": {}})
        self.assertIn("'teamId' is required", str(cm.exception))

    def test_invalid_json_raises_value_error(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            tf.write("{malformed json")
            tf.flush()
            temp_path = Path(tf.name)
        try:
            with self.assertRaises(ValueError) as cm:
                load_config(temp_path)
            self.assertIn("invalid JSON", str(cm.exception))
        finally:
            temp_path.unlink()

    def test_load_default_when_no_file(self) -> None:
        cfg = load_config(Path("/nonexistent/.pr-recap.json"))
        self.assertIsNotNone(cfg.team_id)
        self.assertEqual(cfg.state_map["inProgress"], CANONICAL_STATES["inProgress"])


class TestLinearClientReliability(unittest.TestCase):
    """Test Linear client error handling, bounded retries, and token security."""

    def test_missing_api_key_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            LinearClient(api_key="")

    @patch("urllib.request.urlopen")
    def test_retry_on_500_error(self, mock_urlopen: MagicMock) -> None:
        # Simulate 500 error on first attempt, success on second
        from urllib.error import HTTPError

        err_response = HTTPError("url", 500, "Server Error", {}, None)  # type: ignore
        success_mock = MagicMock()
        success_mock.read.return_value = json.dumps({"data": {"issue": None}}).encode(
            "utf-8"
        )
        success_mock.__enter__.return_value = success_mock
        success_mock.__exit__.return_value = False

        mock_urlopen.side_effect = [err_response, success_mock]

        client = LinearClient(api_key="test-api-key", max_retries=2, timeout=1.0)
        with patch("time.sleep"):  # Speed up tests
            issue = client.get_issue("ABHI-100")
            self.assertIsNone(issue)
            self.assertEqual(mock_urlopen.call_count, 2)

    def test_graphql_error_raised_without_leaking_key(self) -> None:
        client = LinearClient(api_key="secret-linear-token")
        with patch("urllib.request.urlopen") as mock_urlopen:
            resp_mock = MagicMock()
            resp_mock.read.return_value = json.dumps(
                {"errors": [{"message": "Entity not found"}]}
            ).encode("utf-8")
            resp_mock.__enter__.return_value = resp_mock
            resp_mock.__exit__.return_value = False
            mock_urlopen.return_value = resp_mock

            with self.assertRaises(LinearApiError) as cm:
                client.get_issue("NONEXISTENT-999")
            self.assertIn("Entity not found", str(cm.exception))
            self.assertNotIn("secret-linear-token", str(cm.exception))

    def test_find_issue_by_attachment_url(self) -> None:
        client = LinearClient(api_key="test-api-key")
        with patch("urllib.request.urlopen") as mock_urlopen:
            resp_mock = MagicMock()
            resp_mock.read.return_value = json.dumps(
                {
                    "data": {
                        "attachments": {
                            "nodes": [
                                {
                                    "issue": {
                                        "id": "uuid-123",
                                        "identifier": "ABHI-2516",
                                        "title": "Mirrored Issue",
                                        "state": {
                                            "id": "state-1",
                                            "name": "Done",
                                            "type": "completed",
                                        },
                                        "comments": {"nodes": []},
                                        "attachments": {"nodes": []},
                                    }
                                }
                            ]
                        }
                    }
                }
            ).encode("utf-8")
            resp_mock.__enter__.return_value = resp_mock
            resp_mock.__exit__.return_value = False
            mock_urlopen.return_value = resp_mock

            issue = client.find_issue_by_attachment_url("issues/535")
            self.assertIsNotNone(issue)
            self.assertEqual(issue.identifier, "ABHI-2516")
            self.assertEqual(issue.title, "Mirrored Issue")
            self.assertEqual(issue.state.name, "Done")


class TestEndToEndSync(unittest.TestCase):
    """Test end-to-end sync, CLI invocation, and safe no-op handling."""

    @patch.dict(os.environ, {}, clear=True)
    @patch("pr_recap.resolve_linear_api_key", return_value=("fake-key", "env"))
    def test_sync_no_issue_keys_is_safe_noop(self, mock_key: MagicMock) -> None:
        parser = pr_recap.build_parser()
        args = parser.parse_args(
            [
                "sync",
                "--branch",
                "main",
                "--pr-title",
                "Routine dependency updates",
                "--commit-message",
                "chore: bump deps",
            ]
        )
        config = Config.from_dict({"teamId": "test-team"})
        with (
            patch("pr_recap.load_config", return_value=config),
            patch("pr_recap._run_cmd") as mock_cmd,
            patch("pr_recap.LinearClient", autospec=True) as mock_client,
            patch("pr_recap.GitNexusAnalyzer", autospec=True) as mock_analyzer,
            self.assertLogs("pr_recap", level="INFO") as logs,
        ):
            # Local Git state must not add issue references to the fixture.
            mock_cmd.return_value.returncode = 1
            mock_cmd.return_value.stdout = ""
            exit_code = run_sync(args)

        self.assertEqual(exit_code, 0)
        mock_key.assert_called_once_with(config=config, timeout=8.0)
        mock_client.assert_called_once_with(api_key="fake-key")
        self.assertEqual(mock_client.return_value.mock_calls, [])
        mock_analyzer.assert_not_called()
        self.assertIn("safe no-op", "\n".join(logs.output))
        self.assertNotIn("fake-key", "\n".join(logs.output))

    @patch.dict(os.environ, {}, clear=True)
    def test_sync_no_issue_keys_without_credentials(self) -> None:
        """Missing credentials fail normally but allow a dry-run no-op."""
        config = Config.from_dict({"teamId": "test-team"})
        for dry_run, expected_code, expected_log in (
            (False, 1, "Linear API key could not be resolved"),
            (True, 0, "safe no-op"),
        ):
            with self.subTest(dry_run=dry_run):
                argv = ["sync", "--branch", "main", "--commit-message", "chore: tidy"]
                if dry_run:
                    argv.append("--dry-run")
                args = pr_recap.build_parser().parse_args(argv)
                with (
                    patch("pr_recap.load_config", return_value=config),
                    patch("pr_recap._run_cmd") as mock_cmd,
                    patch(
                        "pr_recap.resolve_linear_api_key", return_value=(None, "none")
                    ) as mock_key,
                    patch("pr_recap.LinearClient", autospec=True) as mock_client,
                    patch("pr_recap.GitNexusAnalyzer", autospec=True) as mock_analyzer,
                    self.assertLogs("pr_recap", level="INFO") as logs,
                ):
                    mock_cmd.return_value.returncode = 1
                    mock_cmd.return_value.stdout = ""
                    exit_code = run_sync(args)

                self.assertEqual(exit_code, expected_code)
                mock_key.assert_called_once_with(config=config, timeout=8.0)
                mock_client.assert_not_called()
                mock_analyzer.assert_not_called()
                self.assertIn(expected_log, "\n".join(logs.output))

    def test_sync_dry_run(self) -> None:
        parser = pr_recap.build_parser()
        args = parser.parse_args(
            [
                "sync",
                "--branch",
                "feature/ENG-500-test",
                "--pr-title",
                "Fixes ENG-500",
                "--dry-run",
            ]
        )
        exit_code = run_sync(args)
        self.assertEqual(exit_code, 0)

    def test_github_actions_event_mapping(self) -> None:
        event_data = {
            "action": "ready_for_review",
            "pull_request": {
                "number": 123,
                "title": "Fix memory leak (Fixes ABHI-777)",
                "body": "Resolves issue described in ABHI-777",
                "html_url": "https://github.com/org/repo/pull/123",
                "draft": False,
                "merged": False,
                "state": "open",
                "head": {
                    "ref": "fix/ABHI-777-leak",
                    "sha": "abcdef123456",
                },
            },
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump(event_data, tf)
            tf.flush()
            event_file = Path(tf.name)

        try:
            parser = pr_recap.build_parser()
            args = parser.parse_args(
                [
                    "sync",
                    "--event-path",
                    str(event_file),
                    "--dry-run",
                ]
            )
            ctx = pr_recap.resolve_pr_context(args)
            self.assertEqual(ctx.pr_number, 123)
            self.assertEqual(ctx.action, "ready_for_review")
            self.assertEqual(ctx.branch_name, "fix/ABHI-777-leak")
            self.assertFalse(ctx.is_draft)
            self.assertFalse(ctx.is_merged)
            self.assertEqual(ctx.diff_url, "https://github.com/org/repo/pull/123.diff")

            issues = extract_issue_keys(
                branch_name=ctx.branch_name,
                pr_title=ctx.pr_title,
                pr_body=ctx.pr_body,
            )
            self.assertEqual(issues.get("ABHI-777"), "closes")
        finally:
            event_file.unlink()


class TestSecretResolution(unittest.TestCase):
    """Test provider-agnostic secret resolution (env -> 1Password -> Proton Pass)."""

    def setUp(self) -> None:
        self.config = Config(
            team_id="personal-config",
            state_map=dict(CANONICAL_STATES),
            secret_references={
                "onepassword": "op://Personal/LINEAR_API_KEY/credential",
                "protonpass": {
                    "vault": "Personal",
                    "item": "LINEAR_API_KEY",
                    "field": "Secret",
                },
            },
        )

    @patch.dict(os.environ, {"LINEAR_API_KEY": "env-secret-token"})
    def test_resolve_from_env(self) -> None:
        key, source = pr_recap.resolve_linear_api_key(self.config)
        self.assertEqual(key, "env-secret-token")
        self.assertEqual(source, "environment")

    @patch.dict(os.environ, {}, clear=True)
    @patch("pr_recap._find_onepassword_binary", return_value="/usr/local/bin/op")
    @patch("subprocess.run")
    def test_resolve_from_onepassword(
        self, mock_run: MagicMock, mock_find_op: MagicMock
    ) -> None:
        mock_proc = MagicMock()
        mock_proc.return_value.returncode = 0
        mock_proc.return_value.stdout = "op-resolved-token\n"
        mock_run.return_value = mock_proc.return_value

        key, source = pr_recap.resolve_linear_api_key(self.config)
        self.assertEqual(key, "op-resolved-token")
        self.assertEqual(source, "1password")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(
            cmd,
            [
                "/usr/local/bin/op",
                "read",
                "--force",
                "op://Personal/LINEAR_API_KEY/credential",
            ],
        )

    @patch.dict(os.environ, {}, clear=True)
    @patch("pr_recap._find_onepassword_binary", return_value="/usr/local/bin/op")
    @patch(
        "pr_recap._find_protonpass_binary",
        return_value="/Users/user/.local/bin/pass-cli",
    )
    @patch("subprocess.run")
    def test_resolve_from_protonpass_fallback(
        self,
        mock_run: MagicMock,
        mock_find_pass: MagicMock,
        mock_find_op: MagicMock,
    ) -> None:
        # First call (op read) fails with exit code 1
        op_fail = MagicMock(returncode=1, stdout="", stderr="1Password locked")
        # Second call (pass-cli item view) succeeds with update notices
        pass_success = MagicMock(
            returncode=0,
            stdout="New update available: v2.2.3 -> v2.4.2\n\nproton-secret-token\n",
            stderr="",
        )
        mock_run.side_effect = [op_fail, pass_success]

        key, source = pr_recap.resolve_linear_api_key(self.config)
        self.assertEqual(key, "proton-secret-token")
        self.assertEqual(source, "protonpass")

    @patch.dict(os.environ, {}, clear=True)
    @patch("pr_recap._find_onepassword_binary", return_value=None)
    @patch("pr_recap._find_protonpass_binary", return_value=None)
    def test_resolve_none_when_unavailable(
        self, mock_pass: MagicMock, mock_op: MagicMock
    ) -> None:
        key, source = pr_recap.resolve_linear_api_key(self.config)
        self.assertIsNone(key)
        self.assertEqual(source, "none")

    @patch.dict(os.environ, {}, clear=True)
    @patch("pr_recap._find_onepassword_binary", return_value="/usr/local/bin/op")
    @patch("subprocess.run")
    def test_no_secret_leaked_in_logs(
        self, mock_run: MagicMock, mock_find_op: MagicMock
    ) -> None:
        raw_secret = "super-secret-raw-linear-token-value"
        mock_proc = MagicMock(returncode=0, stdout=f"{raw_secret}\n")
        mock_run.return_value = mock_proc

        with self.assertLogs("pr_recap", level="DEBUG") as log_capture:
            key, source = pr_recap.resolve_linear_api_key(self.config)
            self.assertEqual(key, raw_secret)
            # Ensure the secret value is NEVER logged
            for record in log_capture.records:
                self.assertNotIn(raw_secret, record.getMessage())

    def test_config_custom_secret_references(self) -> None:
        cfg = Config.from_dict(
            {
                "teamId": "custom-team",
                "secretReferences": {
                    "onepassword": "op://VaultX/ItemY/fieldZ",
                    "protonpass": {
                        "vault": "VaultP",
                        "item": "ItemP",
                        "field": "FieldP",
                    },
                },
            }
        )
        self.assertEqual(
            cfg.secret_references["onepassword"], "op://VaultX/ItemY/fieldZ"
        )
        self.assertEqual(cfg.secret_references["protonpass"]["vault"], "VaultP")
        self.assertEqual(cfg.secret_references["protonpass"]["item"], "ItemP")
        self.assertEqual(cfg.secret_references["protonpass"]["field"], "FieldP")


if __name__ == "__main__":
    unittest.main()
