"""Tests for GitHub HTTP client utilities in scripts/pr_lifecycle_github_http.py."""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_github_http as gh_http  # noqa: E402


class TestCasError(unittest.TestCase):
    """Verify CasError initialization and attributes."""

    def test_default_initialization(self) -> None:
        err = gh_http.CasError()
        self.assertEqual(err.code, gh_http.OPERATOR_ERROR)
        self.assertIsNone(err.http_code)
        self.assertEqual(str(err), gh_http.OPERATOR_ERROR)
        self.assertIsInstance(err, ValueError)

    def test_custom_code_and_http_code(self) -> None:
        err = gh_http.CasError(gh_http.OPERATOR_CONFLICT, http_code=409)
        self.assertEqual(err.code, gh_http.OPERATOR_CONFLICT)
        self.assertEqual(err.http_code, 409)
        self.assertEqual(str(err), gh_http.OPERATOR_CONFLICT)


class TestGithubToken(unittest.TestCase):
    """Verify github_token lookup and fail-closed behaviors."""

    def test_prefers_gh_token_over_github_token(self) -> None:
        with patch.dict(os.environ, {"GH_TOKEN": "gh_secret", "GITHUB_TOKEN": "other_secret"}, clear=True):
            self.assertEqual(gh_http.github_token(), "gh_secret")

    def test_falls_back_to_github_token(self) -> None:
        with patch.dict(os.environ, {"GITHUB_TOKEN": "fallback_secret"}, clear=True):
            self.assertEqual(gh_http.github_token(), "fallback_secret")

    def test_raises_cas_error_when_both_unset(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(gh_http.CasError):
                gh_http.github_token()

    def test_raises_cas_error_when_both_empty(self) -> None:
        with patch.dict(os.environ, {"GH_TOKEN": "", "GITHUB_TOKEN": ""}, clear=True):
            with self.assertRaises(gh_http.CasError):
                gh_http.github_token()


class TestGithubApiUrl(unittest.TestCase):
    """Verify github_api_url validation and SSRF/origin safety."""

    def test_valid_rooted_path(self) -> None:
        url = gh_http.github_api_url("/repos/owner/repo/pulls")
        self.assertEqual(url, f"{gh_http.GITHUB_API_ORIGIN}/repos/owner/repo/pulls")

    def test_unrooted_path_raises_cas_error(self) -> None:
        with self.assertRaises(gh_http.CasError):
            gh_http.github_api_url("repos/owner/repo/pulls")

    def test_empty_path_raises_cas_error(self) -> None:
        with self.assertRaises(gh_http.CasError):
            gh_http.github_api_url("")

    def test_whitespace_or_malformed_url_raises(self) -> None:
        with self.assertRaises(ValueError):
            gh_http.github_api_url("/foo bar")

    def test_absolute_url_path_raises_cas_error(self) -> None:
        with self.assertRaises(gh_http.CasError):
            gh_http.github_api_url("https://evil.com/api")

    def test_path_must_be_rooted_under_github_api_origin(self) -> None:
        # Check that a valid url starts with GITHUB_API_ORIGIN + "/"
        url = gh_http.github_api_url("/user")
        self.assertTrue(url.startswith(f"{gh_http.GITHUB_API_ORIGIN}/"))


class TestGithubHeaders(unittest.TestCase):
    """Verify header generation for GitHub API requests."""

    def test_github_headers_contains_required_fields(self) -> None:
        headers = gh_http._github_headers("dummy-token-123")
        self.assertEqual(headers["Accept"], "application/vnd.github+json")
        self.assertEqual(headers["Authorization"], "Bearer dummy-token-123")
        self.assertEqual(headers["X-GitHub-Api-Version"], gh_http.API_VERSION)
        self.assertEqual(headers["User-Agent"], gh_http.USER_AGENT)


class TestDrainHttpErrorBody(unittest.TestCase):
    """Verify _drain_http_error_body reads and drains the response body."""

    def test_drains_body(self) -> None:
        mock_error = urllib.error.HTTPError(
            url="https://api.github.com/test",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=io.BytesIO(b"error-payload"),
        )
        gh_http._drain_http_error_body(mock_error)
        self.assertEqual(mock_error.read(), b"")


class TestPreparedGithubCall(unittest.TestCase):
    """Verify request preparation including method, payload, and headers."""

    def test_prepared_call_without_body(self) -> None:
        req = gh_http._prepared_github_call("GET", "/user", None, "test-token")
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(req.full_url, f"{gh_http.GITHUB_API_ORIGIN}/user")
        self.assertIsNone(req.data)
        self.assertEqual(req.headers["Authorization"], "Bearer test-token")
        self.assertEqual(req.headers["Accept"], "application/vnd.github+json")

    def test_prepared_call_with_json_body(self) -> None:
        payload = {"title": "Test PR", "draft": True}
        req = gh_http._prepared_github_call("POST", "/repos/o/r/pulls", payload, "token-abc")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.full_url, f"{gh_http.GITHUB_API_ORIGIN}/repos/o/r/pulls")
        self.assertIsNotNone(req.data)
        self.assertEqual(json.loads(req.data.decode("utf-8")), payload)
        self.assertEqual(req.headers["Authorization"], "Bearer token-abc")


class TestReadGithubResponse(unittest.TestCase):
    """Verify response reading, resource cleanup, and error handling."""

    def test_successful_read(self) -> None:
        mock_handle = MagicMock()
        mock_handle.read.return_value = b'{"status": "ok"}'
        req = urllib.request.Request("https://api.github.com/test")

        with patch.object(gh_http._HTTPS_OPENER, "open", return_value=mock_handle):
            body = gh_http._read_github_response(req)

        self.assertEqual(body, b'{"status": "ok"}')
        mock_handle.close.assert_called_once()

    def test_http_error_drains_body_and_raises_cas_error_without_body_in_message(self) -> None:
        secret_body = b'{"error": "super-sensitive-token-leak"}'
        error = urllib.error.HTTPError(
            url="https://api.github.com/test",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=io.BytesIO(secret_body),
        )
        req = urllib.request.Request("https://api.github.com/test")

        with patch.object(gh_http._HTTPS_OPENER, "open", side_effect=error):
            with self.assertRaises(gh_http.CasError) as ctx:
                gh_http._read_github_response(req)

        self.assertEqual(ctx.exception.http_code, 403)
        self.assertEqual(ctx.exception.code, gh_http.OPERATOR_ERROR)
        self.assertNotIn("super-sensitive-token-leak", str(ctx.exception))
        # Ensure body stream was drained
        self.assertEqual(error.read(), b"")


class TestGithubRequest(unittest.TestCase):
    """Verify github_request end-to-end execution and JSON parsing."""

    def test_successful_get_json(self) -> None:
        mock_handle = MagicMock()
        mock_handle.read.return_value = b'{"login": "testuser", "id": 12345}'

        with patch.object(gh_http._HTTPS_OPENER, "open", return_value=mock_handle):
            res = gh_http.github_request("GET", "/user", token="mock-token")

        self.assertEqual(res, {"login": "testuser", "id": 12345})

    def test_empty_response_returns_empty_dict(self) -> None:
        mock_handle = MagicMock()
        mock_handle.read.return_value = b""

        with patch.object(gh_http._HTTPS_OPENER, "open", return_value=mock_handle):
            res = gh_http.github_request("DELETE", "/repos/o/r/branches/b", token="mock-token")

        self.assertEqual(res, {})


if __name__ == "__main__":
    unittest.main()
