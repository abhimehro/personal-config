"""Retry, payload parsing, and page execution over the gh api graphql transport."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from pr_lifecycle_inventory_transport import _is_transient_gql_error


def _all_transient(errors: Any) -> bool:
    """True only for a non-empty list of transient GraphQL errors."""
    return (
        isinstance(errors, list)
        and bool(errors)
        and all(_is_transient_gql_error(err) for err in errors)
    )


def _transient_errors(payload: Any) -> list[Any] | None:
    """Return the all-transient errors list, or None when the payload has none.

    Raise OSError when a GraphQL errors payload is not fully transient.
    """
    if not (isinstance(payload, dict) and "errors" in payload):
        return None
    errors = payload["errors"]
    if not _all_transient(errors):
        raise OSError("gh api graphql returned an API error")
    return errors


def _parse_payload(stdout: str) -> tuple[OSError | None, Any]:
    """Return (None, decoded JSON) or (OSError, None) for invalid JSON."""
    try:
        return None, json.loads(stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        return OSError(f"gh api graphql returned invalid JSON: {exc}"), None


def _page_result(
    result: subprocess.CompletedProcess[str],
) -> tuple[OSError | None, Any]:
    """Classify one gh api graphql response.

    Return (retryable OSError, None) for failures worth retrying, or
    (None, payload) on success. Raise OSError for an errors payload that is
    not a non-empty list of entirely transient errors. Structured error
    types take precedence over messages when classifying transient errors.
    """
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return (
            OSError(f"gh api graphql failed rc={result.returncode}: {stderr[:160]}"),
            None,
        )
    error, payload = _parse_payload(result.stdout)
    if error is not None:
        return error, None
    errors = _transient_errors(payload)
    if errors is None:
        return None, payload
    messages = " ".join(str(err.get("message", "")) for err in errors).lower()
    return OSError(f"gh api graphql transient error: {messages[:160]}"), None


def _graphql_page(command: list[str], *, run: Any, sleep: Any) -> Any:
    """Return a decoded GraphQL page after at most three attempts.

    Retry process failures, nonzero exits, invalid JSON, and transient API
    errors with 2- and 4-second waits. Raise OSError immediately for
    nontransient API errors or after exhausting retryable failures.
    """
    last_error: OSError | None = None
    for attempt in range(3):
        try:
            result = run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            last_error = OSError(
                f"gh api graphql process failed: {type(exc).__name__}: {exc}"
            )
        else:
            last_error, payload = _page_result(result)
            if last_error is None:
                return payload
        if attempt < 2:
            sleep(2 ** (attempt + 1))
    if last_error is None:
        raise OSError("gh api graphql exhausted retries without a recorded error")
    raise last_error
