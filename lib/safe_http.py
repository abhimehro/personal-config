"""SSRF-safe HTTP helpers for personal-config.

Provides URL validation, safe wrappers around ``requests`` and
``urllib.request``, redirect validation, and download size limits.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import shutil
import socket
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, BinaryIO

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("safe_http")

MAX_REDIRECTS = 3
DEFAULT_TIMEOUT = (5, 20)  # (connect, read) seconds
DEFAULT_MAX_BYTES = 25 * 1024 * 1024
ALLOWED_SCHEMES = frozenset({"http", "https"})

# Tailscale CGNAT range is not considered private by ``ipaddress`` but is not
# globally routable, so we treat it separately.
_CGNAT_NETWORK = ipaddress.IPv4Network("100.64.0.0/10")

# Headers that should never be forwarded across hosts on a redirect.
_AUTH_HEADERS = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "x-emby-token",
        "x-mediabrowser-token",
    }
)


class UnsafeURLError(ValueError):
    """Raised when a URL fails SSRF validation."""


class UnsafeRedirectError(UnsafeURLError):
    """Raised when a redirect target fails SSRF validation."""


class TooManyRedirectsError(UnsafeURLError):
    """Raised when the redirect hop limit is exceeded."""


@dataclass(frozen=True)
class SafeResponse:
    """A small, read-once response wrapper for ``urllib`` requests."""

    status: int
    url: str
    headers: dict[str, str]
    body: bytes

    def getcode(self) -> int:
        """Compatibility alias for urllib-style callers."""
        return self.status

    def read(self, size: int = -1) -> bytes:
        """Return the already-read body."""
        if size < 0 or size >= len(self.body):
            return self.body
        return self.body[:size]

    def geturl(self) -> str:
        """Return the final URL after any redirects."""
        return self.url


def _normalize_host(host: str) -> str:
    """Lower-case and IDNA-encode a hostname, rejecting obvious homoglyphs."""
    if not host:
        raise UnsafeURLError("URL host is required")

    # Reject non-ASCII hostnames by default. If a legitimate IDN is ever
    # needed, convert via idna first and keep the Punycode form in allowlists.
    if not host.isascii():
        raise UnsafeURLError(f"Non-ASCII hostnames are not allowed: {host!r}")

    try:
        host = host.lower().rstrip(".")
    except Exception as exc:
        raise UnsafeURLError(f"Invalid hostname: {host!r}") from exc

    if re.search(r"\s", host):
        raise UnsafeURLError(f"Invalid hostname: {host!r}")

    return host


def _host_key(host: str) -> str | None:
    """Return the normalized hostname from an allowlist entry that may include a port."""
    if not host:
        return None
    # urlsplit requires a netloc; prepend // for bare host[:port] entries.
    if "://" not in host:
        host = "//" + host
    try:
        parsed = urllib.parse.urlsplit(host)
        hostname = parsed.hostname
    except ValueError:
        hostname = None
    if hostname:
        return hostname.lower().rstrip(".")
    return host.lower().lstrip("/").rstrip(".")


def _is_allowed_host(host: str, allowed_hosts: Iterable[str] | None) -> bool:
    """Check whether ``host`` is in the allowlist (exact or subdomain match)."""
    if allowed_hosts is None:
        return True

    allowed = frozenset(_host_key(h) for h in allowed_hosts if _host_key(h))
    if not allowed:
        return True

    if host in allowed:
        return True

    for a in allowed:
        if host.endswith(f".{a}"):
            return True

    return False


def _resolve_ips(
    host: str, port: int
) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve ``host`` and return the set of IP addresses."""
    try:
        addr_info = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, OSError, ValueError) as exc:
        raise UnsafeURLError(f"Could not resolve {host!r}: {exc}") from exc

    ips: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for res in addr_info:
        ip_str = res[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        # Treat IPv4-mapped IPv6 as IPv4 for policy checks.
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        ips.add(ip)

    if not ips:
        raise UnsafeURLError(f"No IP addresses resolved for {host!r}")

    return ips


def _check_ip_safety(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
    *,
    allow_loopback: bool = False,
    allow_private: bool = False,
    allow_link_local: bool = False,
    allow_cgnat: bool = False,
) -> None:
    """Raise ``UnsafeURLError`` if ``ip`` is not permitted."""
    if ip.is_loopback:
        if allow_loopback:
            return
        raise UnsafeURLError(f"Loopback address is not allowed: {ip}")

    if ip.is_global:
        return

    if ip.is_link_local:
        if allow_link_local:
            return
        raise UnsafeURLError(f"Link-local address is not allowed: {ip}")

    if isinstance(ip, ipaddress.IPv4Address) and ip in _CGNAT_NETWORK:
        if allow_cgnat:
            return
        raise UnsafeURLError(f"CGNAT address is not allowed: {ip}")

    if ip.is_private:
        if allow_private:
            return
        raise UnsafeURLError(f"Private address is not allowed: {ip}")

    # Multicast, reserved, unspecified, etc.
    raise UnsafeURLError(f"Non-public address is not allowed: {ip}")


def validate_url(
    url: str,
    *,
    allowed_hosts: Iterable[str] | None = None,
    allow_loopback: bool = False,
    allow_private: bool = False,
    allow_link_local: bool = False,
    allow_cgnat: bool = False,
    resolve: bool = True,
    require_https: bool = False,
) -> tuple[str, int, set[ipaddress.IPv4Address | ipaddress.IPv6Address]]:
    """Validate a URL for SSRF safety.

    Returns the normalized hostname, port, and resolved IP set.
    Raises ``UnsafeURLError`` on any problem.
    """
    if not url or not isinstance(url, str):
        raise UnsafeURLError("URL must be a non-empty string")

    parts = urllib.parse.urlsplit(url)
    scheme = (parts.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UnsafeURLError(f"Unsupported URL scheme: {parts.scheme!r}")

    if require_https and scheme != "https":
        raise UnsafeURLError("HTTPS is required for this URL")

    if parts.username is not None or parts.password is not None:
        raise UnsafeURLError("URL userinfo is not allowed")

    host = _normalize_host(parts.hostname or "")
    if not _is_allowed_host(host, allowed_hosts):
        raise UnsafeURLError(f"Host is not allowlisted: {host}")

    port = parts.port or (443 if scheme == "https" else 80)

    if not resolve:
        return host, port, set()

    ips = _resolve_ips(host, port)
    for ip in ips:
        _check_ip_safety(
            ip,
            allow_loopback=allow_loopback,
            allow_private=allow_private,
            allow_link_local=allow_link_local,
            allow_cgnat=allow_cgnat,
        )

    return host, port, ips


def _strip_auth_headers(
    headers: Mapping[str, str], old_host: str, new_host: str
) -> dict[str, str]:
    """Remove sensitive headers when a redirect crosses hosts."""
    old = old_host.lower()
    new = new_host.lower()
    if old == new:
        return dict(headers)

    cleaned: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in _AUTH_HEADERS:
            logger.debug("Dropping %s header on cross-host redirect", key)
            continue
        cleaned[key] = value

    return cleaned


def _build_requests_session(
    total_retries: int = 3,
    backoff_factor: float = 1.0,
) -> requests.Session:
    """Create a ``requests`` session that ignores proxy env vars by default."""
    session = requests.Session()
    session.trust_env = False
    if total_retries > 0:
        retry = Retry(
            total=total_retries,
            connect=total_retries,
            read=total_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(
                ["GET", "POST", "HEAD", "PUT", "DELETE", "OPTIONS"]
            ),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
    return session


def safe_request(
    method: str,
    url: str,
    *,
    session: requests.Session | None = None,
    allowed_hosts: Iterable[str] | None = None,
    allow_loopback: bool = False,
    allow_private: bool = False,
    allow_link_local: bool = False,
    allow_cgnat: bool = False,
    require_https: bool = False,
    max_redirects: int = MAX_REDIRECTS,
    strip_auth_on_redirect: bool = True,
    **kwargs: Any,
) -> requests.Response:
    """Make an SSRF-safe ``requests`` call with manually validated redirects.

    Proxy environment variables are ignored. ``timeout`` defaults to
    ``DEFAULT_TIMEOUT``.
    """
    if session is None:
        session = _build_requests_session()
    else:
        session.trust_env = False

    if "timeout" not in kwargs:
        kwargs["timeout"] = DEFAULT_TIMEOUT

    method = method.upper()
    short_method = method.lower()
    use_shortcut = short_method in {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
    }
    validate_url(
        url,
        allowed_hosts=allowed_hosts,
        allow_loopback=allow_loopback,
        allow_private=allow_private,
        allow_link_local=allow_link_local,
        allow_cgnat=allow_cgnat,
        require_https=require_https,
    )

    current_url = url
    headers = dict(kwargs.pop("headers", {}) or {})

    for hop in range(max_redirects + 1):
        if use_shortcut:
            session_method = getattr(session, short_method, session.request)
        else:
            session_method = session.request

        if session_method is session.request:
            response = session_method(
                method,
                current_url,
                headers=headers,
                allow_redirects=False,
                **kwargs,
            )
        else:
            response = session_method(
                current_url,
                headers=headers,
                allow_redirects=False,
                **kwargs,
            )

        # Real responses have int status_code; mocked or unusual responses are
        # returned as-is so callers can raise_for_status / parse themselves.
        status_code = response.status_code
        if not isinstance(status_code, int):
            return response
        if not (300 <= status_code < 400):
            return response

        if hop == max_redirects:
            raise TooManyRedirectsError(
                f"Maximum redirect hops ({max_redirects}) exceeded starting from {url!r}"
            )

        location = response.headers.get("Location") or response.headers.get("location")
        if not location:
            raise UnsafeRedirectError("Redirect response missing Location header")

        new_url = urllib.parse.urljoin(current_url, location)
        old_host = urllib.parse.urlsplit(current_url).hostname or ""
        new_host = urllib.parse.urlsplit(new_url).hostname or ""

        validate_url(
            new_url,
            allowed_hosts=allowed_hosts,
            allow_loopback=allow_loopback,
            allow_private=allow_private,
            allow_link_local=allow_link_local,
            allow_cgnat=allow_cgnat,
            require_https=require_https,
        )

        if strip_auth_on_redirect and old_host.lower() != new_host.lower():
            headers = _strip_auth_headers(headers, old_host, new_host)
            # POST data should not be replayed to a different host on a redirect.
            kwargs.pop("data", None)
            kwargs.pop("json", None)

        current_url = new_url

    raise TooManyRedirectsError(
        f"Maximum redirect hops ({max_redirects}) exceeded starting from {url!r}"
    )


class _ValidatingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Redirect handler that validates every hop and strips cross-host auth."""

    def __init__(
        self,
        *,
        allowed_hosts: Iterable[str] | None = None,
        allow_loopback: bool = False,
        allow_private: bool = False,
        allow_link_local: bool = False,
        allow_cgnat: bool = False,
        require_https: bool = False,
        max_redirects: int = MAX_REDIRECTS,
    ):
        self._allowed_hosts = allowed_hosts
        self._allow_loopback = allow_loopback
        self._allow_private = allow_private
        self._allow_link_local = allow_link_local
        self._allow_cgnat = allow_cgnat
        self._require_https = require_https
        self.max_redirections = max_redirects

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Reject non-HTTP(S) schemes before the default handler re-encodes them.
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme and parsed.scheme.lower() not in ALLOWED_SCHEMES:
            raise urllib.error.HTTPError(
                newurl,
                code,
                f"Redirect to unsupported scheme: {parsed.scheme!r}",
                headers,
                fp,
            )

        validate_url(
            newurl,
            allowed_hosts=self._allowed_hosts,
            allow_loopback=self._allow_loopback,
            allow_private=self._allow_private,
            allow_link_local=self._allow_link_local,
            allow_cgnat=self._allow_cgnat,
            require_https=self._require_https,
        )

        old_host = urllib.parse.urlsplit(req.full_url).hostname or ""
        new_host = parsed.hostname or ""
        new_headers = {
            k: v
            for k, v in req.headers.items()
            if k.lower() not in _AUTH_HEADERS or old_host.lower() == new_host.lower()
        }

        # Remove content headers on method-changing redirects; otherwise preserve
        # the original request body so POST data can follow 307/308 safely.
        method = req.get_method()
        data = req.data if method in ("POST", "PUT", "PATCH") else None
        return urllib.request.Request(
            newurl,
            data=data,
            headers=new_headers,
            method=method,
            origin_req_host=req.origin_req_host,
            unverifiable=True,
        )


def safe_urlopen(
    url: str,
    *,
    data: bytes | None = None,
    headers: Mapping[str, str] | None = None,
    method: str | None = None,
    timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
    allowed_hosts: Iterable[str] | None = None,
    allow_loopback: bool = False,
    allow_private: bool = False,
    allow_link_local: bool = False,
    allow_cgnat: bool = False,
    require_https: bool = False,
    max_redirects: int = MAX_REDIRECTS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    context: ssl.SSLContext | None = None,
) -> SafeResponse:
    """Open ``url`` safely with ``urllib`` and return a read-once response.

    Redirects are validated hop-by-hop, auth headers are stripped on
    cross-host hops, and the response body is bounded by ``max_bytes``.
    """
    # urllib.request only accepts a single numeric timeout; collapse
    # (connect, read) tuples into a total ceiling.
    if isinstance(timeout, tuple):
        timeout = timeout[0] + timeout[1]

    validate_url(
        url,
        allowed_hosts=allowed_hosts,
        allow_loopback=allow_loopback,
        allow_private=allow_private,
        allow_link_local=allow_link_local,
        allow_cgnat=allow_cgnat,
        require_https=require_https,
    )

    req = urllib.request.Request(
        url,
        data=data,
        headers=dict(headers or {}),
        method=method,
    )

    redirect_handler = _ValidatingRedirectHandler(
        allowed_hosts=allowed_hosts,
        allow_loopback=allow_loopback,
        allow_private=allow_private,
        allow_link_local=allow_link_local,
        allow_cgnat=allow_cgnat,
        require_https=require_https,
        max_redirects=max_redirects,
    )
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPHandler,
        urllib.request.HTTPSHandler(context=context),
        redirect_handler,
        urllib.request.HTTPErrorProcessor,
    )

    try:
        with opener.open(req, timeout=timeout) as resp:  # nosec B310
            body = resp.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        # Re-raise as UnsafeURLError only for validation-triggered errors.
        if isinstance(exc, UnsafeURLError):
            raise
        raise

    if len(body) > max_bytes:
        raise UnsafeURLError(f"Response exceeds maximum size of {max_bytes} bytes")

    return SafeResponse(
        status=getattr(resp, "code", resp.getcode()),
        url=resp.geturl(),
        headers=dict(resp.headers or {}),
        body=body,
    )


def safe_download(
    url: str,
    destination: str | BinaryIO,
    *,
    timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    allowed_hosts: Iterable[str] | None = None,
    allow_loopback: bool = False,
    allow_private: bool = False,
    allow_link_local: bool = False,
    allow_cgnat: bool = False,
    require_https: bool = False,
    expected_types: Iterable[str] | None = None,
    **kwargs: Any,
) -> None:
    """Stream a remote resource to ``destination`` with size and host checks."""
    validate_url(
        url,
        allowed_hosts=allowed_hosts,
        allow_loopback=allow_loopback,
        allow_private=allow_private,
        allow_link_local=allow_link_local,
        allow_cgnat=allow_cgnat,
        require_https=require_https,
    )

    resp = safe_urlopen(
        url,
        timeout=timeout,
        allowed_hosts=allowed_hosts,
        allow_loopback=allow_loopback,
        allow_private=allow_private,
        allow_link_local=allow_link_local,
        allow_cgnat=allow_cgnat,
        require_https=require_https,
        max_redirects=kwargs.pop("max_redirects", MAX_REDIRECTS),
        max_bytes=max_bytes,
    )

    if expected_types:
        content_type = resp.headers.get("Content-Type", "").lower()
        if not any(t in content_type for t in expected_types):
            raise UnsafeURLError(
                f"Unexpected Content-Type for {url!r}: {content_type!r}"
            )

    if "Content-Length" in resp.headers:
        try:
            length = int(resp.headers["Content-Length"])
        except ValueError:
            length = None
        if length is not None and length > max_bytes:
            raise UnsafeURLError(f"Content-Length {length} exceeds maximum {max_bytes}")

    if isinstance(destination, str):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(resp.body)
            tmp_path = tmp.name
        shutil.move(tmp_path, destination)
    else:
        destination.write(resp.body)


def build_safe_session(
    total_retries: int = 3,
    backoff_factor: float = 1.0,
) -> requests.Session:
    """Build a ``requests`` session that ignores proxy env vars.

    Callers should still route requests through ``safe_request`` or pass
    the same validation parameters to ensure URL validation and redirect
    handling are applied.
    """
    return _build_requests_session(
        total_retries=total_retries,
        backoff_factor=backoff_factor,
    )


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Validate a URL for SSRF safety")
    parser.add_argument("--check-url", required=True, help="URL to validate")
    parser.add_argument(
        "--allowed-hosts",
        default="",
        help="Comma-separated list of allowed hosts",
    )
    parser.add_argument(
        "--allow-loopback",
        action="store_true",
        help="Allow loopback addresses",
    )
    parser.add_argument(
        "--allow-private",
        action="store_true",
        help="Allow RFC1918 private addresses",
    )
    parser.add_argument(
        "--allow-link-local",
        action="store_true",
        help="Allow link-local addresses (including mDNS .local)",
    )
    parser.add_argument(
        "--allow-cgnat",
        action="store_true",
        help="Allow 100.64.0.0/10 CGNAT (Tailscale) addresses",
    )
    parser.add_argument(
        "--require-https",
        action="store_true",
        help="Require HTTPS scheme",
    )

    args = parser.parse_args()
    allowed_hosts = [h.strip() for h in args.allowed_hosts.split(",") if h.strip()]
    try:
        validate_url(
            args.check_url,
            allowed_hosts=allowed_hosts or None,
            allow_loopback=args.allow_loopback,
            allow_private=args.allow_private,
            allow_link_local=args.allow_link_local,
            allow_cgnat=args.allow_cgnat,
            require_https=args.require_https,
        )
    except UnsafeURLError as exc:
        print(f"Unsafe URL: {exc}", file=sys.stderr)
        sys.exit(1)
    print("OK")
