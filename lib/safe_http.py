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

# HTTP methods that can use the convenience methods on ``requests.Session``.
_SHORT_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})

# HTTP methods that may carry a request body.
_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})

# Safety options shared by the public helpers. Populated from ``**kwargs``.
_SAFETY_DEFAULTS: dict[str, Any] = {
    "allowed_hosts": None,
    "allow_loopback": False,
    "allow_private": False,
    "allow_link_local": False,
    "allow_cgnat": False,
    "require_https": False,
    "max_redirects": MAX_REDIRECTS,
    "max_bytes": DEFAULT_MAX_BYTES,
    "strip_auth_on_redirect": True,
}
_SAFETY_KEYS = frozenset(_SAFETY_DEFAULTS.keys())


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


def _extract_safety_options(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Pop safety-related keys from ``kwargs`` and return them as a dict."""
    return {key: kwargs.pop(key, _SAFETY_DEFAULTS[key]) for key in _SAFETY_KEYS}


def _normalize_host(host: str) -> str:
    """Lower-case and IDNA-encode a hostname, rejecting obvious homoglyphs."""
    if not host:
        raise UnsafeURLError("URL host is required")
    if not host.isascii():
        raise UnsafeURLError(f"Non-ASCII hostnames are not allowed: {host!r}")
    if re.search(r"\s", host):
        raise UnsafeURLError(f"Invalid hostname: {host!r}")
    return host.lower().rstrip(".")


def _host_key(host: str) -> str | None:
    """Return the normalized hostname from an allowlist entry that may include a port."""
    if host:
        if "://" in host:
            netloc = host
        else:
            netloc = "//" + host
        try:
            hostname = urllib.parse.urlsplit(netloc).hostname
        except ValueError:
            hostname = None
        if hostname:
            return hostname.lower().rstrip(".")
        return netloc.lower().lstrip("/").rstrip(".")
    return None


def _allowed_host_set(allowed_hosts: Iterable[str]) -> set[str]:
    """Build a normalized set of allowlisted hostnames."""
    allowed: set[str] = set()
    for entry in allowed_hosts:
        key = _host_key(entry)
        if key:
            allowed.add(key)
    return allowed


def _is_subdomain(host: str, allowed: set[str]) -> bool:
    """Return True when ``host`` is a subdomain of an entry in ``allowed``."""
    for entry in allowed:
        if host.endswith(f".{entry}"):
            return True
    return False


def _is_allowed_host(host: str, allowed_hosts: Iterable[str] | None) -> bool:
    """Check whether ``host`` is in the allowlist (exact or subdomain match)."""
    if allowed_hosts is None:
        return True
    allowed = _allowed_host_set(allowed_hosts)
    if allowed:
        if host in allowed:
            return True
        return _is_subdomain(host, allowed)
    return True


def _parse_addr_info(
    addr_info: list,
) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Convert the result of ``getaddrinfo`` into a set of IP addresses."""
    ips: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for res in addr_info:
        ip = _parse_addr_entry(res)
        if ip:
            ips.add(ip)
    return ips


def _parse_addr_entry(
    res: tuple,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Parse a single ``getaddrinfo`` result tuple into an IP address."""
    ip_str = res[4][0]
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip


def _resolve_ips(
    host: str, port: int
) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve ``host`` and return the set of IP addresses."""
    try:
        addr_info = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, OSError, ValueError) as exc:
        raise UnsafeURLError(f"Could not resolve {host!r}: {exc}") from exc
    ips = _parse_addr_info(addr_info)
    if ips:
        return ips
    raise UnsafeURLError(f"No IP addresses resolved for {host!r}")


def _is_cgnat(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if ``ip`` is in the Tailscale CGNAT range."""
    return isinstance(ip, ipaddress.IPv4Address) and ip in _CGNAT_NETWORK


def _check_ip_category(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
    flag: str,
    label: str,
    options: dict[str, Any],
) -> None:
    """Raise ``UnsafeURLError`` if the flagged IP category is not allowed."""
    if options.get(flag):
        return
    raise UnsafeURLError(f"{label} is not allowed: {ip}")


def _check_ip_safety(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address, options: dict[str, Any]
) -> None:
    """Raise ``UnsafeURLError`` if ``ip`` is not permitted."""
    if ip.is_global:
        return
    checks = (
        (ip.is_loopback, "allow_loopback", "Loopback address"),
        (ip.is_link_local, "allow_link_local", "Link-local address"),
        (ip.is_private, "allow_private", "Private address"),
        (_is_cgnat(ip), "allow_cgnat", "CGNAT address"),
    )
    for is_category, flag, label in checks:
        if is_category:
            _check_ip_category(ip, flag, label, options)
            return
    raise UnsafeURLError(f"Non-public address is not allowed: {ip}")


def _check_ip_set(
    ips: set[ipaddress.IPv4Address | ipaddress.IPv6Address], options: dict[str, Any]
) -> None:
    """Validate every resolved IP against the safety policy."""
    for ip in ips:
        _check_ip_safety(ip, options)


def _validate_url_string(url: Any) -> urllib.parse.SplitResult:
    """Ensure ``url`` is a non-empty string and parse it."""
    if url and isinstance(url, str):
        return urllib.parse.urlsplit(url)
    raise UnsafeURLError("URL must be a non-empty string")


def _validate_scheme(scheme: str, options: dict[str, Any]) -> str:
    """Validate and normalize the URL scheme."""
    scheme = scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UnsafeURLError(f"Unsupported URL scheme: {scheme!r}")
    if options.get("require_https") and scheme != "https":
        raise UnsafeURLError("HTTPS is required for this URL")
    return scheme


def _validate_userinfo(parts: urllib.parse.SplitResult) -> None:
    """Reject URLs that contain embedded credentials."""
    if parts.username is not None or parts.password is not None:
        raise UnsafeURLError("URL userinfo is not allowed")


def _resolve_port(scheme: str, explicit_port: int | None) -> int:
    """Return the port, using scheme defaults when omitted."""
    if explicit_port is not None:
        return explicit_port
    return 443 if scheme == "https" else 80


def _validate_host(host: str | None, allowed_hosts: Iterable[str] | None) -> str:
    """Normalize and allowlist-check a hostname."""
    host = _normalize_host(host)
    if _is_allowed_host(host, allowed_hosts):
        return host
    raise UnsafeURLError(f"Host is not allowlisted: {host}")


def validate_url(
    url: str,
    *,
    resolve: bool = True,
    **safety_kwargs: Any,
) -> tuple[str, int, set[ipaddress.IPv4Address | ipaddress.IPv6Address]]:
    """Validate a URL for SSRF safety.

    Returns the normalized hostname, port, and resolved IP set.
    Raises ``UnsafeURLError`` on any problem.
    """
    options = _extract_safety_options(safety_kwargs)
    parts = _validate_url_string(url)
    scheme = _validate_scheme(parts.scheme, options)
    _validate_userinfo(parts)
    host = _validate_host(parts.hostname, options.get("allowed_hosts"))
    port = _resolve_port(scheme, parts.port)
    if resolve:
        ips = _resolve_ips(host, port)
        _check_ip_set(ips, options)
        return host, port, ips
    return host, port, set()


def _strip_auth_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Remove sensitive headers from a header dict."""
    cleaned: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in _AUTH_HEADERS:
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
    if total_retries <= 0:
        return session
    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST", "HEAD", "PUT", "DELETE", "OPTIONS"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _method_shortcut(method: str) -> str | None:
    """Return the lowercase method name if it maps to a Session helper."""
    short = method.lower()
    return short if short in _SHORT_METHODS else None


def _send_one_request(
    session: requests.Session,
    method: str,
    short: str | None,
    url: str,
    request_kwargs: dict[str, Any],
) -> requests.Response:
    """Send a single request without following redirects."""
    if short is None:
        return session.request(method, url, allow_redirects=False, **request_kwargs)
    return getattr(session, short)(url, allow_redirects=False, **request_kwargs)


def _is_redirect_response(response: requests.Response) -> bool:
    """Return True if the response is an HTTP redirect and status is numeric."""
    status = response.status_code
    if isinstance(status, int):
        return 300 <= status < 400
    return False


def _extract_redirect_url(current_url: str, response: requests.Response) -> str:
    """Resolve the Location header into an absolute URL."""
    location = response.headers.get("Location")
    if location is None:
        location = response.headers.get("location")
    if location:
        return urllib.parse.urljoin(current_url, location)
    raise UnsafeRedirectError("Redirect response missing Location header")


def _same_host(old_url: str, new_url: str) -> bool:
    """Compare the hostnames of two URLs case-insensitively."""
    old_host = urllib.parse.urlsplit(old_url).hostname
    new_host = urllib.parse.urlsplit(new_url).hostname
    if old_host is None:
        old_host = ""
    if new_host is None:
        new_host = ""
    return old_host.lower() == new_host.lower()


def _sanitize_redirect_kwargs(
    request_kwargs: dict[str, Any],
    old_url: str,
    new_url: str,
    options: dict[str, Any],
) -> None:
    """Strip auth headers and body when a redirect crosses hosts."""
    if options.get("strip_auth_on_redirect", True):
        if _same_host(old_url, new_url):
            return
        request_kwargs["headers"] = _strip_auth_headers(request_kwargs["headers"])
        request_kwargs.pop("data", None)
        request_kwargs.pop("json", None)


def _request_with_redirects(
    session: requests.Session,
    method: str,
    short: str | None,
    current_url: str,
    request_kwargs: dict[str, Any],
    options: dict[str, Any],
    remaining: int,
) -> requests.Response:
    """Follow redirects manually while re-validating each hop."""
    response = _send_one_request(session, method, short, current_url, request_kwargs)
    if _is_redirect_response(response):
        if remaining <= 0:
            raise TooManyRedirectsError(
                f"Maximum redirect hops ({options['max_redirects']}) exceeded starting from {current_url!r}"
            )
        new_url = _extract_redirect_url(current_url, response)
        validate_url(new_url, **options)
        _sanitize_redirect_kwargs(request_kwargs, current_url, new_url, options)
        return _request_with_redirects(
            session, method, short, new_url, request_kwargs, options, remaining - 1
        )
    return response


def safe_request(
    method: str,
    url: str,
    *,
    session: requests.Session | None = None,
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

    options = _extract_safety_options(kwargs)
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)

    if kwargs.get("headers") is None:
        kwargs["headers"] = {}
    else:
        kwargs["headers"] = dict(kwargs["headers"])

    method = method.upper()
    short = _method_shortcut(method)
    validate_url(url, **options)
    return _request_with_redirects(
        session, method, short, url, kwargs, options, options["max_redirects"]
    )


def _is_allowed_scheme(scheme: str | None) -> bool:
    """Return True when the scheme is missing or in the allowed set."""
    if scheme is None:
        return True
    return scheme.lower() in ALLOWED_SCHEMES


def _redirect_body(req: urllib.request.Request) -> bytes | None:
    """Preserve the request body for methods that may carry one."""
    method = req.get_method()
    if method in _BODY_METHODS:
        return req.data
    return None


def _filter_headers(
    headers: dict[str, str], old_host: str, new_host: str, strip_auth: bool
) -> dict[str, str]:
    """Preserve auth headers only when the redirect stays on the same host."""
    if strip_auth and old_host.lower() != new_host.lower():
        cleaned: dict[str, str] = {}
        for key, value in headers.items():
            if key.lower() in _AUTH_HEADERS:
                continue
            cleaned[key] = value
        return cleaned
    return dict(headers)


class _ValidatingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Redirect handler that validates every hop and strips cross-host auth."""

    def __init__(self, **safety_kwargs: Any):
        self._options = _extract_safety_options(safety_kwargs)
        self.max_redirections = self._options["max_redirects"]

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Validate the redirect and build a sanitized follow-up request."""
        parsed = urllib.parse.urlsplit(newurl)
        if not _is_allowed_scheme(parsed.scheme):
            raise urllib.error.HTTPError(
                newurl,
                code,
                f"Redirect to unsupported scheme: {parsed.scheme!r}",
                headers,
                fp,
            )

        validate_url(newurl, **self._options)

        old_host = urllib.parse.urlsplit(req.full_url).hostname or ""
        new_host = parsed.hostname or ""
        strip_auth = self._options.get("strip_auth_on_redirect", True)
        new_headers = _filter_headers(req.headers, old_host, new_host, strip_auth)

        method = req.get_method()
        data = _redirect_body(req)
        return urllib.request.Request(
            newurl,
            data=data,
            headers=new_headers,
            method=method,
            origin_req_host=req.origin_req_host,
            unverifiable=True,
        )


def _collapse_timeout(timeout: float | tuple[float, float]) -> float:
    """Collapse a (connect, read) tuple into a single numeric timeout."""
    if isinstance(timeout, tuple):
        return timeout[0] + timeout[1]
    return timeout


def _build_safe_opener(
    redirect_handler: urllib.request.HTTPRedirectHandler,
    context: ssl.SSLContext | None,
) -> urllib.request.OpenerDirector:
    """Assemble an opener that ignores proxies and uses the validating handler."""
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPHandler,
        urllib.request.HTTPSHandler(context=context),
        redirect_handler,
        urllib.request.HTTPErrorProcessor,
    )


def _read_body(
    opener: urllib.request.OpenerDirector,
    req: urllib.request.Request,
    timeout: float,
    max_bytes: int,
) -> tuple[Any, bytes]:
    """Open the request and read up to ``max_bytes + 1`` bytes."""
    with opener.open(req, timeout=timeout) as resp:  # nosec B310
        body = resp.read(max_bytes + 1)
    return resp, body


def _make_safe_response(resp: Any, body: bytes, max_bytes: int) -> SafeResponse:
    """Build a ``SafeResponse`` and enforce the size limit."""
    if len(body) > max_bytes:
        raise UnsafeURLError(f"Response exceeds maximum size of {max_bytes} bytes")
    return SafeResponse(
        status=getattr(resp, "code", resp.getcode()),
        url=resp.geturl(),
        headers=dict(resp.headers or {}),
        body=body,
    )


def safe_urlopen(
    url: str,
    *,
    data: bytes | None = None,
    headers: Mapping[str, str] | None = None,
    method: str | None = None,
    timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
    context: ssl.SSLContext | None = None,
    **safety_kwargs: Any,
) -> SafeResponse:
    """Open ``url`` safely with ``urllib`` and return a read-once response.

    Redirects are validated hop-by-hop, auth headers are stripped on
    cross-host hops, and the response body is bounded by ``max_bytes``.
    """
    options = _extract_safety_options(safety_kwargs)
    timeout = _collapse_timeout(timeout)
    validate_url(url, **options)

    req = urllib.request.Request(
        url,
        data=data,
        headers=dict(headers or {}),
        method=method,
    )

    redirect_handler = _ValidatingRedirectHandler(**options)
    opener = _build_safe_opener(redirect_handler, context)
    resp, body = _read_body(opener, req, timeout, options["max_bytes"])
    return _make_safe_response(resp, body, options["max_bytes"])


def _check_content_type(
    headers: dict[str, str], expected_types: Iterable[str], url: str
) -> None:
    """Raise if the response Content-Type is not in the expected set."""
    content_type = headers.get("Content-Type", "").lower()
    for t in expected_types:
        if t in content_type:
            return
    raise UnsafeURLError(f"Unexpected Content-Type for {url!r}: {content_type!r}")


def _check_content_length(headers: dict[str, str], max_bytes: int) -> None:
    """Raise if the declared Content-Length exceeds the maximum."""
    raw = headers.get("Content-Length")
    if raw is None:
        return
    try:
        length = int(raw)
    except ValueError:
        return
    if length > max_bytes:
        raise UnsafeURLError(f"Content-Length {length} exceeds maximum {max_bytes}")


def _write_destination(destination: str | BinaryIO, body: bytes) -> None:
    """Write the downloaded body to a path or file-like object."""
    if isinstance(destination, str):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(body)
            tmp_path = tmp.name
        shutil.move(tmp_path, destination)
    else:
        destination.write(body)


def safe_download(
    url: str,
    destination: str | BinaryIO,
    *,
    timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
    expected_types: Iterable[str] | None = None,
    **safety_kwargs: Any,
) -> None:
    """Stream a remote resource to ``destination`` with size and host checks."""
    options = _extract_safety_options(safety_kwargs)
    resp = safe_urlopen(url, timeout=timeout, **options)
    max_bytes = options["max_bytes"]
    if expected_types:
        _check_content_type(resp.headers, expected_types, url)
    _check_content_length(resp.headers, max_bytes)
    _write_destination(destination, resp.body)


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


def _safety_flags(
    allow_loopback: bool,
    allow_private: bool,
    allow_link_local: bool,
    allow_cgnat: bool,
    require_https: bool,
) -> dict[str, bool]:
    """Bundle the boolean safety flags for CLI callers."""
    return {
        "allow_loopback": allow_loopback,
        "allow_private": allow_private,
        "allow_link_local": allow_link_local,
        "allow_cgnat": allow_cgnat,
        "require_https": require_https,
    }


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
    flags = _safety_flags(
        args.allow_loopback,
        args.allow_private,
        args.allow_link_local,
        args.allow_cgnat,
        args.require_https,
    )
    try:
        validate_url(
            args.check_url,
            allowed_hosts=allowed_hosts or None,
            **flags,
        )
    except UnsafeURLError as exc:
        print(f"Unsafe URL: {exc}", file=sys.stderr)
        sys.exit(1)
    print("OK")
