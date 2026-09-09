"""HTTPS-only GitHub API client for lifecycle ledger CAS (no response bodies)."""

# Extracted from the CAS orchestrator so that file stays under the NLOC gate.
# Callers must pass a token. GitHub response bodies never reach stderr.

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
# SECURITY: HTTPS-only opener — default urlopen also registers file:// and ftp://.
_HTTPS_OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler())

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


def _drain_http_error_body(exc: urllib.error.HTTPError) -> None:
    """SECURITY: consume the GitHub body so it cannot leak to stderr."""
    exc.read()


def _github_headers(token: str) -> dict[str, str]:
    """REST headers for api.github.com. Never log this dict (Bearer token)."""
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": USER_AGENT,
    }


def _read_github_response(request: urllib.request.Request) -> bytes:
    """Open an HTTPS-only request. HTTP errors become CasError without bodies."""
    try:
        with _HTTPS_OPENER.open(request, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        _drain_http_error_body(exc)
        raise CasError(http_code=exc.code) from None


def github_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    token: str,
) -> Any:
    """JSON GET/POST/PATCH against api.github.com. Token is a required kwarg."""
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        github_api_url(path),
        data=payload,
        method=method,
        headers=_github_headers(token),
    )
    raw_body = _read_github_response(request)
    if not raw_body:
        return {}
    return json.loads(raw_body.decode("utf-8"))
