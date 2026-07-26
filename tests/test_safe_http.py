"""Unit tests for lib.safe_http SSRF helpers."""

from __future__ import annotations

import http.server
import ipaddress
import os
import socket
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

from lib import safe_http

_HOST_IPS = {
    "127.0.0.1": ["127.0.0.1"],
    "localhost": ["127.0.0.1"],
    "::1": ["::1"],
    "example.com": ["1.1.1.1"],
    "other.example.com": ["1.1.1.1"],
    "sub.example.com": ["1.1.1.1"],
    "private.example.com": ["192.168.1.5"],
    "metadata.example.com": ["169.254.169.254"],
    "cgnat.example.com": ["100.64.0.5"],
    "mapped.example.com": ["::ffff:127.0.0.1"],
}


def _addr_record(ip_str: str, port: int) -> tuple:
    """Build a single ``getaddrinfo``-style tuple for an IP string."""
    ip = ipaddress.ip_address(ip_str)
    if isinstance(ip, ipaddress.IPv6Address):
        return (socket.AF_INET6, socket.SOCK_STREAM, 0, "", (str(ip), port, 0, 0))
    return (socket.AF_INET, socket.SOCK_STREAM, 0, "", (str(ip), port))


def _is_ip(addr: str) -> bool:
    """Return True when ``addr`` is already a valid IP string."""
    try:
        ipaddress.ip_address(addr)
        return True
    except ValueError:
        return False


def _getaddrinfo_stub(host: str, port: int, *_, **__):
    """Deterministic resolver for tests."""
    ip_strs = _HOST_IPS.get(host)
    if ip_strs is not None:
        return [_addr_record(ip, port) for ip in ip_strs]
    if _is_ip(host):
        return [_addr_record(host, port)]
    return []


@patch("lib.safe_http.socket.getaddrinfo", new=_getaddrinfo_stub)
class TestValidateUrl(unittest.TestCase):
    def test_public_host_allowed(self):
        host, port, ips = safe_http.validate_url("https://example.com/path")
        self.assertEqual(host, "example.com")
        self.assertEqual(port, 443)

    def test_public_ip_allowed(self):
        safe_http.validate_url("http://1.1.1.1/")

    def test_loopback_blocked_by_default(self):
        with self.assertRaises(safe_http.UnsafeURLError):
            safe_http.validate_url("http://127.0.0.1:8096/")

    def test_loopback_allowed(self):
        safe_http.validate_url("http://127.0.0.1:8096/", allow_loopback=True)

    def test_private_host_blocked(self):
        with self.assertRaises(safe_http.UnsafeURLError):
            safe_http.validate_url("http://private.example.com/")

    def test_private_host_allowed(self):
        safe_http.validate_url("http://private.example.com/", allow_private=True)

    def test_metadata_address_blocked(self):
        with self.assertRaises(safe_http.UnsafeURLError):
            safe_http.validate_url("http://metadata.example.com/")

    def test_cgnat_blocked(self):
        with self.assertRaises(safe_http.UnsafeURLError):
            safe_http.validate_url("http://cgnat.example.com/")

    def test_ipv4_mapped_loopback_blocked(self):
        with self.assertRaises(safe_http.UnsafeURLError):
            safe_http.validate_url("http://mapped.example.com/")

    def test_non_http_scheme_rejected(self):
        with self.assertRaises(safe_http.UnsafeURLError):
            safe_http.validate_url("file:///etc/passwd")

    def test_userinfo_rejected(self):
        with self.assertRaises(safe_http.UnsafeURLError):
            safe_http.validate_url("http://api.com@evil.com/")

    def test_allowed_hosts_exact(self):
        safe_http.validate_url(
            "http://private.example.com/",
            allowed_hosts={"private.example.com"},
            allow_private=True,
        )

    def test_allowed_hosts_subdomain(self):
        safe_http.validate_url(
            "http://sub.example.com/",
            allowed_hosts={"example.com"},
        )

    def test_allowed_hosts_with_port(self):
        safe_http.validate_url(
            "http://127.0.0.1:8096/",
            allowed_hosts={"127.0.0.1:8096"},
            allow_loopback=True,
        )

    def test_require_https(self):
        with self.assertRaises(safe_http.UnsafeURLError):
            safe_http.validate_url("http://example.com/", require_https=True)
        safe_http.validate_url("https://example.com/", require_https=True)


@patch("lib.safe_http.socket.getaddrinfo", new=_getaddrinfo_stub)
class TestSafeRequest(unittest.TestCase):
    def _make_session(self, responses):
        session = MagicMock()
        session.request.side_effect = responses
        session.get.side_effect = responses
        session.post.side_effect = responses
        return session

    def test_basic_get(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {}
        session = self._make_session([resp])
        result = safe_http.safe_request("GET", "https://example.com/", session=session)
        self.assertEqual(result, resp)
        session.get.assert_called_once()
        (call_url,) = session.get.call_args[0]
        self.assertEqual(call_url, "https://example.com/")

    def test_cross_host_redirect_strips_auth(self):
        redirect = MagicMock()
        redirect.status_code = 302
        redirect.headers = {"Location": "https://other.example.com/"}
        final = MagicMock()
        final.status_code = 200
        final.headers = {}
        session = self._make_session([redirect, final])

        safe_http.safe_request(
            "GET",
            "https://example.com/",
            session=session,
            headers={"Authorization": "Bearer secret"},
            allowed_hosts={"example.com", "other.example.com"},
        )

        first_call = session.get.call_args_list[0]
        second_call = session.get.call_args_list[1]
        self.assertEqual(first_call.kwargs["headers"]["Authorization"], "Bearer secret")
        self.assertNotIn("Authorization", second_call.kwargs["headers"])

    def test_redirect_to_non_allowed_host_fails(self):
        redirect = MagicMock()
        redirect.status_code = 302
        redirect.headers = {"Location": "https://evil.com/"}
        session = self._make_session([redirect])

        with self.assertRaises(safe_http.UnsafeURLError):
            safe_http.safe_request(
                "GET",
                "https://example.com/",
                session=session,
                allowed_hosts={"example.com"},
            )

    def test_too_many_redirects(self):
        redirect = MagicMock()
        redirect.status_code = 302
        redirect.headers = {"Location": "https://example.com/next"}
        session = self._make_session([redirect] * (safe_http.MAX_REDIRECTS + 1))

        with self.assertRaises(safe_http.TooManyRedirectsError):
            safe_http.safe_request("GET", "https://example.com/", session=session)


class TestSafeUrlopen(unittest.TestCase):
    def _run_server(self, handler):
        server = http.server.HTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        return server, port

    def test_simple_get(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *args):
                pass

        server, port = self._run_server(Handler)
        try:
            resp = safe_http.safe_urlopen(
                f"http://127.0.0.1:{port}/",
                allow_loopback=True,
            )
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.body, b"ok")
        finally:
            server.shutdown()
            server.server_close()

    def test_redirect_to_disallowed_host_fails(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", "http://private.example.com/")
                self.end_headers()

            def log_message(self, *args):
                pass

        server, port = self._run_server(Handler)
        try:
            with self.assertRaises(safe_http.UnsafeURLError):
                safe_http.safe_urlopen(
                    f"http://127.0.0.1:{port}/",
                    allow_loopback=True,
                    allowed_hosts={"127.0.0.1"},
                )
        finally:
            server.shutdown()
            server.server_close()

    def test_size_limit(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", "100")
                self.end_headers()
                self.wfile.write(b"x" * 100)

            def log_message(self, *args):
                pass

        server, port = self._run_server(Handler)
        try:
            with self.assertRaises(safe_http.UnsafeURLError):
                safe_http.safe_urlopen(
                    f"http://127.0.0.1:{port}/",
                    allow_loopback=True,
                    max_bytes=10,
                )
        finally:
            server.shutdown()
            server.server_close()

    def test_safe_download(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", "3")
                self.end_headers()
                self.wfile.write(b"abc")

            def log_message(self, *args):
                pass

        server, port = self._run_server(Handler)
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                dest = tmp.name
            safe_http.safe_download(
                f"http://127.0.0.1:{port}/",
                dest,
                allow_loopback=True,
                max_bytes=10,
            )
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), b"abc")
            os.unlink(dest)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
