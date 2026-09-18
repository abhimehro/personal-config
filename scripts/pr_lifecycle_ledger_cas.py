"""Fetch, restore, and CAS-write the runtime lifecycle ledger via Git Data."""

# Contents GET returns encoding=none above 1 MB. Reads use /git/blobs/<sha>;
# writes fast-forward blob → tree → commit → ref (force=false).
# pylint: disable=wrong-import-position

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# pylint: disable=wrong-import-position
from pr_lifecycle_config import validate_bootstrap_pointer, validate_config
from pr_lifecycle_github_git import (
    contained_output_path,
)
from pr_lifecycle_github_git import create_blob as git_create_blob
from pr_lifecycle_github_git import create_commit as git_create_commit
from pr_lifecycle_github_git import create_tree as git_create_tree
from pr_lifecycle_github_git import decode_github_blob
from pr_lifecycle_github_git import ensure_data_ref as git_ensure_data_ref
from pr_lifecycle_github_git import fetch_runtime_ledger as git_fetch_runtime_ledger
from pr_lifecycle_github_git import is_stale_tip_error, object_sha
from pr_lifecycle_github_git import read_commit as git_read_commit
from pr_lifecycle_github_git import ref_path, tree_sha
from pr_lifecycle_github_git import update_ref as git_update_ref
from pr_lifecycle_github_git import update_ref_path
from pr_lifecycle_github_http import (
    _HTTPS_OPENER,
    GITHUB_API_ORIGIN,
    OPERATOR_CONFLICT,
    OPERATOR_ERROR,
    CasError,
    github_api_url,
)
from pr_lifecycle_github_http import github_request as github_http_request
from pr_lifecycle_github_http import github_token as lookup_github_token
from pr_lifecycle_persist import sanitize_ledger_file
from pr_lifecycle_support import ROOT
from pr_lifecycle_validation import validate
from pr_lifecycle_yaml import load_yaml

DEFAULT_COMMIT_MESSAGE = "automated lifecycle ledger update"
# Re-exports: tests patch cas._HTTPS_OPENER and call cas.github_api_url.
__all__ = [
    "GITHUB_API_ORIGIN",
    "OPERATOR_CONFLICT",
    "OPERATOR_ERROR",
    "_HTTPS_OPENER",
    "CasError",
    "contained_output_path",
    "decode_github_blob",
    "github_api_url",
    "github_request",
    "github_token",
    "is_stale_tip_error",
    "object_sha",
    "ref_path",
    "tree_sha",
    "update_ref_path",
]


def pointer_runtime() -> dict[str, Any]:
    """Load and validate the bootstrap pointer's runtime_ledger mapping."""
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    pointer = load_yaml(ROOT / "tasks/pr-lifecycle-ledger.yaml")
    validate_bootstrap_pointer(pointer, config)
    runtime = pointer["runtime_ledger"]
    if not isinstance(runtime, dict):
        raise TypeError("ledger pointer: runtime_ledger must be a mapping")
    return runtime


def github_token() -> str:
    """Look up GH_TOKEN here so tests can patch ``cas.github_token``."""
    return lookup_github_token()


def github_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> Any:
    """Thin wrapper so token lookup and opener patches stay on this module."""
    return github_http_request(method, path, body, token=github_token())


def ensure_data_ref(runtime: dict[str, Any]) -> dict[str, Any]:
    """Restore the data-branch ref from the pointer SHA when GitHub 404s."""
    return git_ensure_data_ref(runtime, github_request)


def fetch_runtime_ledger(runtime: dict[str, Any], dest: Path) -> dict[str, Any]:
    """Fetch the runtime ledger blob to a contained dest path."""
    return git_fetch_runtime_ledger(runtime, dest, github_request)


def create_blob(content: str) -> str:
    """POST a utf-8 Git blob through the patchable request wrapper."""
    return git_create_blob(content, github_request)


def read_commit(sha: str) -> dict[str, Any]:
    """GET a Git commit through the patchable request wrapper."""
    return git_read_commit(sha, github_request)


def create_tree(base_tree: str, path: str, blob_sha: str) -> str:
    """POST a replacement tree through the patchable request wrapper."""
    return git_create_tree(base_tree, path, blob_sha, github_request)


def create_commit(message: str, tree_sha_value: str, parent_sha: str) -> str:
    """POST a single-parent commit through the patchable request wrapper."""
    return git_create_commit(message, tree_sha_value, parent_sha, github_request)


def update_ref(
    branch: str,
    sha: str,
    expected_sha: str | None = None,
) -> dict[str, Any]:
    """PATCH a branch ref through the patchable request wrapper."""
    return git_update_ref(branch, sha, github_request, expected_sha)


def _fast_forward_or_conflict(
    branch: str,
    commit_sha: str,
    expected_sha: str,
) -> None:
    """PATCH the data-branch ref. Stale tips become OPERATOR_CONFLICT."""
    try:
        update_ref(branch, commit_sha, expected_sha)
    except CasError as exc:
        if is_stale_tip_error(exc):
            raise CasError(OPERATOR_CONFLICT, http_code=exc.http_code) from None
        raise


def cas_commit(runtime: dict[str, Any], content: str, message: str) -> dict[str, Any]:
    """Fast-forward the data branch. Do not retry stale bytes onto a new tip."""
    branch = str(runtime["data_branch"])
    path = str(runtime["data_path"])
    ensured = ensure_data_ref(runtime)
    parent_sha = object_sha(ensured["ref"])
    parent = read_commit(parent_sha)
    blob_sha = create_blob(content)
    new_tree = create_tree(tree_sha(parent), path, blob_sha)
    commit_sha = create_commit(message, new_tree, parent_sha)
    _fast_forward_or_conflict(branch, commit_sha, parent_sha)
    return {
        "commit_sha": commit_sha,
        "blob_sha": blob_sha,
        "parent_sha": parent_sha,
        "restored_ref": bool(ensured["restored"]),
        "attempt": 1,
    }


def run_preflight(out: Path) -> dict[str, Any]:
    """Fetch, sanitize, and validate the runtime ledger without writing GitHub."""
    runtime = pointer_runtime()
    fetch = fetch_runtime_ledger(runtime, out)
    sanitized = sanitize_ledger_file(Path(fetch["path"]), bump_revision=False)
    stripped = validate(Path(fetch["path"]))
    return {
        "ok": True,
        "ref_restored": fetch["restored_ref"],
        "commit_sha": fetch["commit_sha"],
        "blob_sha": fetch["blob_sha"],
        "size": fetch["size"],
        "contents_encoding": fetch["encoding"],
        "sanitized_fields": sanitized["removed_fields"],
        "validator_stripped_fields": stripped,
        "ledger_path": fetch["path"],
    }


def run_commit(file_path: Path, message: str, *, bump_revision: bool) -> dict[str, Any]:
    """Sanitize then CAS-write a local ledger file onto the data branch."""
    runtime = pointer_runtime()
    contained = contained_output_path(file_path)
    # Always line-strip before validate+upload so projection keys cannot re-persist.
    sanitize_ledger_file(contained, bump_revision=bump_revision)
    stripped = validate(contained)
    result = cas_commit(runtime, contained.read_text(encoding="utf-8"), message)
    result["validator_stripped_fields"] = stripped
    return result


def build_parser() -> argparse.ArgumentParser:
    """CLI for preflight fetch and CAS commit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--debug",
        action="store_true",
        help="print exception type and HTTP code; still omit GitHub bodies",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--out", type=Path, required=True)
    commit = sub.add_parser("commit")
    commit.add_argument("--file", type=Path, required=True)
    commit.add_argument("--message", default=DEFAULT_COMMIT_MESSAGE)
    commit.add_argument("--bump-revision", action="store_true")
    return parser


def _print_operator_error(exc: BaseException, *, debug: bool) -> None:
    """Print a stable operator code. Debug adds type and HTTP code only."""
    if isinstance(exc, CasError):
        print(exc.code, file=sys.stderr)
    else:
        print(OPERATOR_ERROR, file=sys.stderr)
    if debug:
        http_code = getattr(exc, "http_code", None)
        print(f"{type(exc).__name__} http_code={http_code}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """Run preflight or commit. Never print GitHub response bodies."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            print(json.dumps(run_preflight(args.out), indent=2))
            return 0
        result = run_commit(args.file, args.message, bump_revision=args.bump_revision)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        _print_operator_error(exc, debug=args.debug)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
