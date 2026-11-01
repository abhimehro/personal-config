"""Unit tests for GitHub HTTP utilities in pr_lifecycle_github_http."""

from __future__ import annotations

import io
import json
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


class CasErrorTests(unittest.TestCase):
    """Verify CasError behavior and exception properties."""

    def test_default_cas_error(self) -> None:
        """CasError defaults to OPERATOR_ERROR with no http_code."""
        err = gh_http.CasError()
        self.assertEqual(err.code, gh_http.OPERATOR_ERROR)
        self.assertIsNone(err.http_code)
        self.assertEqual(str(err), gh_http.OPERATOR_ERROR)
        self.assertIsInstance(err, ValueError)

    def test_custom_code_and_http_code(self) -> None:
        """CasError stores custom operator code and HTTP status code."""
        err = gh_http.CasError(gh_http.OPERATOR_CONFLICT, http_code=409)
        self.assertEqual(err.code, gh_http.OPERATOR_CONFLICT)
        self.assertEqual(err.http_code, 409)
        self.assertEqual(str(err), gh_http.OPERATOR_CONFLICT)


class GithubTokenTests(unittest.TestCase):
    """Verify fail-closed token resolution from environment variables."""

    def test_gh_token_precedence(self) -> None:
        """GH_TOKEN takes precedence over GITHUB_TOKEN."""
        with patch.dict("os.environ", {"GH_TOKEN": "token-gh", "GITHUB_TOKEN": "token-github"}):
            self.assertEqual(gh_http.github_token(), "token-gh")

    def test_github_token_fallback(self) -> None:
        """GITHUB_TOKEN is used when GH_TOKEN is unset."""
        with patch.dict("os.environ", {"GITHUB_TOKEN": "token-github"}, clear=True):
            self.assertEqual(gh_http.github_token(), "token-github")

    def test_tokens_unset_fails_closed(self) -> None:
        """CasError is raised when neither GH_TOKEN nor GITHUB_TOKEN is present."""
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(gh_http.CasError):
                gh_http.github_token()

    def test_empty_tokens_fail_closed(self) -> None:
        """CasError is raised when token variables are present but empty."""
        with patch.dict("os.environ", {"GH_TOKEN": "", "GITHUB_TOKEN": ""}):
            with self.assertRaises(gh_http.CasError):
                gh_http.github_token()


class GithubApiUrlTests(unittest.TestCase):
    """Verify URL generation and origin confinement for GitHub API routes."""

    def test_valid_rooted_path(self) -> None:
        """Rooted API route builds expected HTTPS URL."""
        url = gh_http.github_api_url("/user/repos")
        self.assertEqual(url, f"{gh_http.GITHUB_API_ORIGIN}/user/repos")

    def test_unrooted_path_raises_cas_error(self) -> None:
        """Unrooted relative path is rejected with CasError."""
        with self.assertRaises(gh_http.CasError):
            gh_http.github_api_url("user/repos")

    def test_empty_path_raises_cas_error(self) -> None:
        """Empty path is rejected with CasError."""
        with self.assertRaises(gh_http.CasError):
            gh_http.github_api_url("")

    def test_absolute_url_scheme_raises_cas_error(self) -> None:
        """Full URL strings without leading slash are rejected."""
        with self.assertRaises(gh_http.CasError):
            gh_http.github_api_url("https://evil.example.com/steal")
        with self.assertRaises(gh_http.CasError):
            gh_http.github_api_url("file:///etc/passwd")

    def test_whitespace_in_path_raises_error(self) -> None:
        """Whitespace in path is rejected by require_https_url."""
        with self.assertRaises(ValueError):
            gh_http.github_api_url("/repos/owner/repo/pulls ")


class GithubHeadersTests(unittest.TestCase):
    """Verify standard headers constructed for REST API calls."""

    def test_headers_structure(self) -> None:
        """Headers contain required Accept, Authorization, Version, and User-Agent."""
        headers = gh_http._github_headers("secret-token-xyz")
        self.assertEqual(
            headers,
            {
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer secret-token-xyz",
                "X-GitHub-Api-Version": gh_http.API_VERSION,
                "User-Agent": gh_http.USER_AGENT,
            },
        )


class PreparedGithubCallTests(unittest.TestCase):
    """Verify Request construction for JSON REST calls."""

    def test_request_without_body(self) -> None:
        """GET request without payload is correctly prepared."""
        req = gh_http._prepared_github_call("GET", "/rate_limit", None, "test-token")
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(req.full_url, "https://api.github.com/rate_limit")
        self.assertIsNone(req.data)
        self.assertEqual(req.get_header("Authorization"), "Bearer test-token")
        self.assertEqual(req.get_header("User-agent"), gh_http.USER_AGENT)

    def test_request_with_json_body(self) -> None:
        """POST request serializes dictionary to UTF-8 encoded JSON bytes."""
        payload = {"title": "Update", "draft": False}
        req = gh_http._prepared_github_call("POST", "/repos/o/r/pulls", payload, "test-token")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.full_url, "https://api.github.com/repos/o/r/pulls")
        self.assertEqual(req.data, json.dumps(payload).encode("utf-8"))
        self.assertEqual(req.get_header("Authorization"), "Bearer test-token")


class ReadGithubResponseTests(unittest.TestCase):
    """Verify response reading and error handling via HTTPS-only director."""

    def test_successful_read(self) -> None:
        """Successful response reads bytes and closes handle."""
        mock_handle = MagicMock()
        mock_handle.read.return_value = b'{"status": "ok"}'

        with patch.object(gh_http._HTTPS_OPENER, "open", return_value=mock_handle) as mock_open:
            req = urllib.request.Request("https://api.github.com/test")
            data = gh_http._read_github_response(req)
            self.assertEqual(data, b'{"status": "ok"}')
            mock_open.assert_called_once_with(req, timeout=gh_http.TLS_TIMEOUT_SECONDS)
            mock_handle.close.assert_called_once()

    def test_http_error_drains_body_and_raises_cas_error(self) -> None:
        """HTTPError body is drained to prevent leaking and re-raised as CasError."""
        # SECURITY: ensure response body is read and not included in CasError
        body_stream = io.BytesIO(b'{"message": "Not Found", "documentation_url": "..."}')
        http_error = urllib.error.HTTPError(
            url="https://api.github.com/test",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=body_stream,
        )

        with patch.object(gh_http._HTTPS_OPENER, "open", side_effect=http_error):
            req = urllib.request.Request("https://api.github.com/test")
            with self.assertRaises(gh_http.CasError) as ctx:
                gh_http._read_github_response(req)

            self.assertEqual(ctx.exception.http_code, 404)
            self.assertEqual(ctx.exception.code, gh_http.OPERATOR_ERROR)
            self.assertNotIn("Not Found", str(ctx.exception))
            # Confirm body stream was drained
            self.assertEqual(body_stream.read(), b"")


class GithubRequestTests(unittest.TestCase):
    """Verify high-level github_request parsing and dispatch."""

    def test_github_request_returns_parsed_json(self) -> None:
        """Valid JSON response is parsed into python structures."""
        mock_handle = MagicMock()
        mock_handle.read.return_value = b'{"sha": "12345"}'

        with patch.object(gh_http._HTTPS_OPENER, "open", return_value=mock_handle):
            res = gh_http.github_request("GET", "/repos/o/r/git/ref/head", token="token-1")
            self.assertEqual(res, {"sha": "12345"})

    def test_github_request_empty_body_returns_empty_dict(self) -> None:
        """Empty response body returns empty dictionary."""
        mock_handle = MagicMock()
        mock_handle.read.return_value = b""

        with patch.object(gh_http._HTTPS_OPENER, "open", return_value=mock_handle):
            res = gh_http.github_request("DELETE", "/repos/o/r/git/ref/head", token="token-1")
            self.assertEqual(res, {})


class HttpsOnlyDirectorTests(unittest.TestCase):
    """Verify security boundaries of the custom opener director."""

    def test_director_handlers(self) -> None:
        """OpenerDirector enforces HTTPS-only and disallows plain HTTP or File."""
        director = gh_http._https_only_director()
        handler_types = {type(h) for h in director.handlers}
        self.assertIn(urllib.request.HTTPSHandler, handler_types)
        self.assertNotIn(urllib.request.HTTPHandler, handler_types)
        self.assertNotIn(urllib.request.FileHandler, handler_types)
        self.assertNotIn(urllib.request.FTPHandler, handler_types)


if __name__ == "__main__":
    unittest.main()
