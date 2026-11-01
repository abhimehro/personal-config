"""Unit tests for GitHub HTTP and CAS utilities in scripts/pr_lifecycle_github_http.py."""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_github_http as gh_http  # noqa: E402


class TestCasError(unittest.TestCase):
    """Test CasError initialization, attributes, and exception hierarchy."""

    def test_default_initialization(self) -> None:
        err = gh_http.CasError()
        self.assertIsInstance(err, ValueError)
        self.assertEqual(err.code, gh_http.OPERATOR_ERROR)
        self.assertEqual(str(err), gh_http.OPERATOR_ERROR)
        self.assertIsNone(err.http_code)

    def test_custom_code_and_http_status(self) -> None:
        err = gh_http.CasError(gh_http.OPERATOR_CONFLICT, http_code=409)
        self.assertEqual(err.code, gh_http.OPERATOR_CONFLICT)
        self.assertEqual(str(err), gh_http.OPERATOR_CONFLICT)
        self.assertEqual(err.http_code, 409)


class TestGithubToken(unittest.TestCase):
    """Test resolution of GitHub authentication token from environment."""

    def test_resolves_gh_token(self) -> None:
        with mock.patch.dict(os.environ, {"GH_TOKEN": "token_from_gh"}, clear=True):
            self.assertEqual(gh_http.github_token(), "token_from_gh")

    def test_resolves_github_token_fallback(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "token_from_github"}, clear=True):
            self.assertEqual(gh_http.github_token(), "token_from_github")

    def test_prefers_gh_token_over_github_token(self) -> None:
        env = {"GH_TOKEN": "primary_token", "GITHUB_TOKEN": "secondary_token"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(gh_http.github_token(), "primary_token")

    def test_raises_cas_error_when_both_tokens_unset(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(gh_http.CasError):
                gh_http.github_token()

    def test_raises_cas_error_when_tokens_are_empty(self) -> None:
        with mock.patch.dict(os.environ, {"GH_TOKEN": "", "GITHUB_TOKEN": ""}, clear=True):
            with self.assertRaises(gh_http.CasError):
                gh_http.github_token()


class TestGithubApiUrl(unittest.TestCase):
    """Test GitHub API URL construction and security boundary validation."""

    def test_valid_rooted_api_path(self) -> None:
        url = gh_http.github_api_url("/repos/owner/repo/pulls")
        self.assertEqual(url, f"{gh_http.GITHUB_API_ORIGIN}/repos/owner/repo/pulls")

    def test_valid_rooted_path_with_query_params(self) -> None:
        url = gh_http.github_api_url("/repos/owner/repo/pulls?state=open&per_page=50")
        self.assertEqual(
            url,
            f"{gh_http.GITHUB_API_ORIGIN}/repos/owner/repo/pulls?state=open&per_page=50",
        )

    def test_rejects_unrooted_path(self) -> None:
        for invalid_path in ("repos/owner/repo", "api/v3", ""):
            with self.subTest(path=invalid_path):
                with self.assertRaises(gh_http.CasError):
                    gh_http.github_api_url(invalid_path)

    def test_rejects_non_rooted_relative_attempts(self) -> None:
        with self.assertRaises(gh_http.CasError):
            gh_http.github_api_url("..")


class TestGithubHeadersAndPreparedCall(unittest.TestCase):
    """Test request header composition and Request object preparation."""

    def test_headers_structure(self) -> None:
        headers = gh_http._github_headers("secret_token_123")
        self.assertEqual(
            headers,
            {
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer secret_token_123",
                "X-GitHub-Api-Version": gh_http.API_VERSION,
                "User-Agent": gh_http.USER_AGENT,
            },
        )

    def test_prepared_github_call_without_body(self) -> None:
        request = gh_http._prepared_github_call("GET", "/user", None, "tok_abc")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.full_url, f"{gh_http.GITHUB_API_ORIGIN}/user")
        self.assertIsNone(request.data)
        self.assertEqual(request.headers["Authorization"], "Bearer tok_abc")
        self.assertEqual(request.headers["Accept"], "application/vnd.github+json")

    def test_prepared_github_call_with_body(self) -> None:
        body = {"title": "Test PR", "draft": True}
        request = gh_http._prepared_github_call("POST", "/repos/o/r/pulls", body, "tok_xyz")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url, f"{gh_http.GITHUB_API_ORIGIN}/repos/o/r/pulls")
        self.assertEqual(request.data, json.dumps(body).encode("utf-8"))
        self.assertEqual(request.headers["Authorization"], "Bearer tok_xyz")


class TestDrainHttpErrorBody(unittest.TestCase):
    """Test that failed HTTP error response bodies are drained safely."""

    def test_drain_reads_entire_body(self) -> None:
        body_stream = io.BytesIO(b"error response payload")
        http_error = urllib.error.HTTPError(
            url="https://api.github.com/test",
            code=400,
            msg="Bad Request",
            hdrs=mock.MagicMock(),
            fp=body_stream,
        )
        gh_http._drain_http_error_body(http_error)
        self.assertEqual(body_stream.read(), b"")


class TestGithubRequest(unittest.TestCase):
    """Test github_request execution, success handling, and error mapping."""

    @mock.patch.object(gh_http._HTTPS_OPENER, "open")
    def test_successful_get_request(self, mock_open: mock.MagicMock) -> None:
        payload = {"id": 1, "login": "test-user"}
        mock_response = io.BytesIO(json.dumps(payload).encode("utf-8"))
        mock_open.return_value = mock_response

        result = gh_http.github_request("GET", "/user", token="test_token")
        self.assertEqual(result, payload)
        mock_open.assert_called_once()
        prepared_request = mock_open.call_args[0][0]
        self.assertEqual(prepared_request.get_method(), "GET")
        self.assertEqual(prepared_request.full_url, f"{gh_http.GITHUB_API_ORIGIN}/user")

    @mock.patch.object(gh_http._HTTPS_OPENER, "open")
    def test_empty_response_returns_empty_dict(self, mock_open: mock.MagicMock) -> None:
        mock_response = io.BytesIO(b"")
        mock_open.return_value = mock_response

        result = gh_http.github_request("DELETE", "/repos/o/r/labels/bug", token="test_token")
        self.assertEqual(result, {})

    @mock.patch.object(gh_http._HTTPS_OPENER, "open")
    def test_http_error_mapped_to_cas_error_with_code(self, mock_open: mock.MagicMock) -> None:
        error_file = io.BytesIO(b'{"message": "Not Found"}')
        http_error = urllib.error.HTTPError(
            url="https://api.github.com/nonexistent",
            code=404,
            msg="Not Found",
            hdrs=mock.MagicMock(),
            fp=error_file,
        )
        mock_open.side_effect = http_error

        with self.assertRaises(gh_http.CasError) as ctx:
            gh_http.github_request("GET", "/nonexistent", token="test_token")

        self.assertEqual(ctx.exception.http_code, 404)
        self.assertEqual(ctx.exception.code, gh_http.OPERATOR_ERROR)
        # Verify the error body was consumed
        self.assertEqual(error_file.read(), b"")

    @mock.patch.object(gh_http._HTTPS_OPENER, "open")
    def test_http_conflict_mapped_to_cas_error_with_409(self, mock_open: mock.MagicMock) -> None:
        error_file = io.BytesIO(b'{"message": "Conflict"}')
        http_error = urllib.error.HTTPError(
            url="https://api.github.com/repos/o/r/contents/file",
            code=409,
            msg="Conflict",
            hdrs=mock.MagicMock(),
            fp=error_file,
        )
        mock_open.side_effect = http_error

        with self.assertRaises(gh_http.CasError) as ctx:
            gh_http.github_request("PUT", "/repos/o/r/contents/file", {"message": "update"}, token="tok")

        self.assertEqual(ctx.exception.http_code, 409)


if __name__ == "__main__":
    unittest.main()
