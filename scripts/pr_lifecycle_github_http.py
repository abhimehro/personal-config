"""HTTPS-only GitHub API client for lifecycle ledger CAS.

Extracted from `pr_lifecycle_ledger_cas.py` so the CAS orchestrator stays below
the file-level complexity gate. Callers must pass a token; this module never
prints GitHub response bodies.
"""

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


class CasError(ValueError):
    """Operator-safe CAS failure. GitHub response bodies stay off stderr."""

    def __init__(
        self,
        code: str = OPERATOR_ERROR,
        *,
        http_code: int | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.http_code = http_code


def github_token() -> str:
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


def github_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    token: str,
) -> Any:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        github_api_url(path),
        data=payload,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with _HTTPS_OPENER.open(request, timeout=60) as response:
            raw_body = response.read()
    except urllib.error.HTTPError as exc:
        _drain_http_error_body(exc)
        raise CasError(http_code=exc.code) from None
    if not raw_body:
        return {}
    parsed: Any = json.loads(raw_body.decode("utf-8"))
    return parsed
