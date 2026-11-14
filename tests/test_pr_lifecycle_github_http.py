"""Unit tests for scripts/pr_lifecycle_github_http.py."""

from __future__ import annotations

import io
import json
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_github_http as gh_http  # noqa: E402


class TestCasError(unittest.TestCase):
    """Test CasError initialization and attributes."""

    def test_default_initialization(self) -> None:
        err = gh_http.CasError()
        self.assertIsInstance(err, ValueError)
        self.assertEqual(err.code, gh_http.OPERATOR_ERROR)
        self.assertIsNone(err.http_code)
        self.assertEqual(str(err), gh_http.OPERATOR_ERROR)

    def test_custom_code_and_http_status(self) -> None:
        err = gh_http.CasError(gh_http.OPERATOR_CONFLICT, http_code=409)
        self.assertEqual(err.code, gh_http.OPERATOR_CONFLICT)
        self.assertEqual(err.http_code, 409)
        self.assertEqual(str(err), gh_http.OPERATOR_CONFLICT)


class TestGithubToken(unittest.TestCase):
    """Test github_token environment resolution."""

    def test_token_missing_raises_cas_error(self) -> None:
        with mock.patch.dict(gh_http.os.environ, {}, clear=True):
            with self.assertRaises(gh_http.CasError) as ctx:
                gh_http.github_token()
            self.assertEqual(ctx.exception.code, gh_http.OPERATOR_ERROR)

    def test_gh_token_precedence(self) -> None:
        env = {"GH_TOKEN": "gh_secret_123", "GITHUB_TOKEN": "github_secret_456"}
        with mock.patch.dict(gh_http.os.environ, env, clear=True):
            self.assertEqual(gh_http.github_token(), "gh_secret_123")

    def test_github_token_fallback(self) -> None:
        env = {"GITHUB_TOKEN": "github_secret_456"}
        with mock.patch.dict(gh_http.os.environ, env, clear=True):
            self.assertEqual(gh_http.github_token(), "github_secret_456")


class TestGithubApiUrl(unittest.TestCase):
    """Test github_api_url validation and URL construction."""

    def test_valid_rooted_api_route(self) -> None:
        url = gh_http.github_api_url("/repos/owner/repo/pulls")
        self.assertEqual(url, "https://api.github.com/repos/owner/repo/pulls")

    def test_unrooted_path_raises_cas_error(self) -> None:
        with self.assertRaises(gh_http.CasError):
            gh_http.github_api_url("repos/owner/repo/pulls")

    def test_empty_path_raises_cas_error(self) -> None:
        with self.assertRaises(gh_http.CasError):
            gh_http.github_api_url("")

    def test_path_not_starting_with_origin_slash_raises_cas_error(self) -> None:
        # If path does not start with "/" after origin
        with mock.patch.object(gh_http, "GITHUB_API_ORIGIN", "http://insecure.api.github.com"):
            with self.assertRaises(Exception):
                gh_http.github_api_url("/test")


class TestGithubHeaders(unittest.TestCase):
    """Test _github_headers creation."""

    def test_headers_structure(self) -> None:
        headers = gh_http._github_headers("test-token-xyz")
        self.assertEqual(headers["Accept"], "application/vnd.github+json")
        self.assertEqual(headers["Authorization"], "Bearer test-token-xyz")
        self.assertEqual(headers["X-GitHub-Api-Version"], gh_http.API_VERSION)
        self.assertEqual(headers["User-Agent"], gh_http.USER_AGENT)


class TestDrainHttpErrorBody(unittest.TestCase):
    """Test _drain_http_error_body consumes the response."""

    def test_drain_reads_error_body(self) -> None:
        err = urllib.error.HTTPError(
            url="https://api.github.com/test",
            code=400,
            msg="Bad Request",
            hdrs={},  # type: ignore[arg-type]
            fp=io.BytesIO(b"body"),
        )
        gh_http._drain_http_error_body(err)
        self.assertEqual(err.read(), b"")


class TestPreparedGithubCall(unittest.TestCase):
    """Test _prepared_github_call request preparation."""

    def test_prepared_call_without_body(self) -> None:
        req = gh_http._prepared_github_call(
            "GET",
            "/user",
            None,
            "token-abc",
        )
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(req.full_url, "https://api.github.com/user")
        self.assertIsNone(req.data)
        self.assertEqual(req.get_header("Authorization"), "Bearer token-abc")
        self.assertEqual(req.get_header("User-agent"), gh_http.USER_AGENT)

    def test_prepared_call_with_body(self) -> None:
        body = {"title": "Test PR", "draft": True}
        req = gh_http._prepared_github_call(
            "POST",
            "/repos/o/r/pulls",
            body,
            "token-def",
        )
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.full_url, "https://api.github.com/repos/o/r/pulls")
        self.assertIsNotNone(req.data)
        self.assertEqual(json.loads(req.data.decode("utf-8")), body)
        self.assertEqual(req.get_header("Authorization"), "Bearer token-def")


class TestReadGithubResponse(unittest.TestCase):
    """Test _read_github_response dispatching through _HTTPS_OPENER."""

    def test_read_success_returns_bytes_and_closes_handle(self) -> None:
        mock_handle = mock.MagicMock()
        mock_handle.read.return_value = b'{"status": "ok"}'

        with mock.patch.object(gh_http._HTTPS_OPENER, "open", return_value=mock_handle) as mock_open:
            req = urllib.request.Request("https://api.github.com/test")
            raw_bytes = gh_http._read_github_response(req)

            mock_open.assert_called_once_with(req, timeout=gh_http.TLS_TIMEOUT_SECONDS)
            mock_handle.read.assert_called_once()
            mock_handle.close.assert_called_once()
            self.assertEqual(raw_bytes, b'{"status": "ok"}')

    def test_read_http_error_drains_body_and_raises_cas_error(self) -> None:
        mock_err = urllib.error.HTTPError(
            url="https://api.github.com/test",
            code=404,
            msg="Not Found",
            hdrs={},  # type: ignore[arg-type]
            fp=io.BytesIO(b'{"message": "Secret leak or not found"}'),
        )
        with mock.patch.object(gh_http._HTTPS_OPENER, "open", side_effect=mock_err):
            with mock.patch.object(gh_http, "_drain_http_error_body") as mock_drain:
                req = urllib.request.Request("https://api.github.com/test")
                with self.assertRaises(gh_http.CasError) as ctx:
                    gh_http._read_github_response(req)

                mock_drain.assert_called_once_with(mock_err)
                self.assertEqual(ctx.exception.http_code, 404)
                self.assertEqual(ctx.exception.code, gh_http.OPERATOR_ERROR)


class TestGithubRequest(unittest.TestCase):
    """Test github_request high-level function."""

    @mock.patch.object(gh_http, "_read_github_response")
    @mock.patch.object(gh_http, "_prepared_github_call")
    def test_github_request_parses_json(
        self,
        mock_prepared: mock.MagicMock,
        mock_read: mock.MagicMock,
    ) -> None:
        dummy_req = mock.MagicMock(spec=urllib.request.Request)
        mock_prepared.return_value = dummy_req
        mock_read.return_value = b'{"id": 42, "name": "test"}'

        result = gh_http.github_request(
            "GET",
            "/repos/o/r",
            token="test-token",
        )

        mock_prepared.assert_called_once_with("GET", "/repos/o/r", None, "test-token")
        mock_read.assert_called_once_with(dummy_req)
        self.assertEqual(result, {"id": 42, "name": "test"})

    @mock.patch.object(gh_http, "_read_github_response")
    @mock.patch.object(gh_http, "_prepared_github_call")
    def test_github_request_empty_response(
        self,
        mock_prepared: mock.MagicMock,
        mock_read: mock.MagicMock,
    ) -> None:
        dummy_req = mock.MagicMock(spec=urllib.request.Request)
        mock_prepared.return_value = dummy_req
        mock_read.return_value = b""

        result = gh_http.github_request(
            "DELETE",
            "/repos/o/r/git/refs/heads/feature",
            token="test-token",
        )

        self.assertEqual(result, {})


class TestDirectorHttpsOnly(unittest.TestCase):
    """Test _https_only_director handlers."""

    def test_director_handlers(self) -> None:
        director = gh_http._https_only_director()
        handler_classes = [h.__class__ for h in director.handlers]
        self.assertIn(urllib.request.HTTPSHandler, handler_classes)
        self.assertNotIn(urllib.request.HTTPHandler, handler_classes)
        self.assertNotIn(urllib.request.FileHandler, handler_classes)
        self.assertNotIn(urllib.request.FTPHandler, handler_classes)


if __name__ == "__main__":
    unittest.main()
