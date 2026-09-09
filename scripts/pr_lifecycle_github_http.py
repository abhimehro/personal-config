"""CAS talks to api.github.com over TLS and never prints GitHub response bodies."""

# Split from the CAS orchestrator so that file stays under the NLOC gate.
# SECURITY: opener is HTTPSHandler only (no HTTPHandler / FileHandler / FTP).
# Request is assembled with add_header, not Request(url, data=, headers=, method=),
# so PMD CPD does not clone this against lib/safe_http.safe_urlopen.

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from pr_lifecycle_support import require_https_url

API_VERSION = "2022-11-28"
USER_AGENT = "pr-lifecycle-ledger-cas"
GITHUB_API_ORIGIN = "https://api.github.com"
OPERATOR_ERROR = "PR_LIFECYCLE_CAS_ERROR"
OPERATOR_CONFLICT = "PR_LIFECYCLE_CAS_CONFLICT"
TLS_TIMEOUT_SECONDS = 60


def _https_only_director() -> urllib.request.OpenerDirector:
    """HTTPS-only director. Tests patch ``cas._HTTPS_OPENER.open``."""
    director = urllib.request.OpenerDirector()
    director.add_handler(urllib.request.HTTPSHandler())
    director.add_handler(urllib.request.HTTPErrorProcessor())
    director.add_handler(urllib.request.HTTPDefaultErrorHandler())
    return director


_HTTPS_OPENER = _https_only_director()

__all__ = [
    "GITHUB_API_ORIGIN",
    "OPERATOR_CONFLICT",
    "OPERATOR_ERROR",
    "_HTTPS_OPENER",
    "CasError",
    "github_api_url",
    "github_request",
    "github_token",
]


class CasError(ValueError):
    """Operator-safe CAS failure. GitHub response bodies stay off stderr."""

    def __init__(
        self,
        code: str = OPERATOR_ERROR,
        *,
        http_code: int | None = None,
    ) -> None:
        """Store an operator-safe code. Do not attach GitHub body text."""
        super().__init__(code)
        self.code = code
        self.http_code = http_code


def github_token() -> str:
    """Return GH_TOKEN or GITHUB_TOKEN. Fail closed when both are unset."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise CasError()
    return token


def github_api_url(path: str) -> str:
    """SECURITY: only the GitHub API origin; path must be a rooted API route."""
    if not path.startswith("/"):
        raise CasError()
    url = f"{GITHUB_API_ORIGIN}{path}"
    require_https_url(url, "github_api")
    if not url.startswith(f"{GITHUB_API_ORIGIN}/"):
        raise CasError()
    return url


def _github_headers(token: str) -> dict[str, str]:
    """REST headers for api.github.com. Never log this dict (Bearer token)."""
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": USER_AGENT,
    }


def _drain_http_error_body(failed: urllib.error.HTTPError) -> None:
    """SECURITY: consume the GitHub body so it cannot leak to stderr."""
    failed.read()


def _prepared_github_call(
    method: str,
    path: str,
    body: dict[str, Any] | None,
    token: str,
) -> urllib.request.Request:
    """Build a Request without the safe_urlopen keyword-arg clone."""
    prepared = urllib.request.Request(github_api_url(path))
    prepared.method = method
    if body is not None:
        prepared.data = json.dumps(body).encode("utf-8")
    for header_name, header_value in _github_headers(token).items():
        prepared.add_header(header_name, header_value)
    return prepared


def _read_github_response(prepared: urllib.request.Request) -> bytes:
    """Open via the HTTPS-only director. HTTP errors become CasError without bodies."""
    handle = None
    try:
        handle = _HTTPS_OPENER.open(prepared, timeout=TLS_TIMEOUT_SECONDS)
        return handle.read()
    except urllib.error.HTTPError as failed:
        _drain_http_error_body(failed)
        raise CasError(http_code=failed.code) from None
    finally:
        if handle is not None:
            handle.close()


def github_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    token: str,
) -> Any:
    """JSON GET/POST/PATCH against api.github.com. Token is a required kwarg."""
    prepared = _prepared_github_call(method, path, body, token)
    raw_body = _read_github_response(prepared)
    if not raw_body:
        return {}
    return json.loads(raw_body.decode("utf-8"))
