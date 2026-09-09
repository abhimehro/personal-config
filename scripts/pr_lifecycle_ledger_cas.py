"""Fetch, restore, and CAS-write the runtime lifecycle ledger.

The selected primitive remains `github_contents_api`, but GitHub Contents GET
returns `encoding: none` (empty body) for files larger than 1 MB. This helper
reads via `GET /git/blobs/<sha>` and writes via Git Data API fast-forward
(blob → tree → commit → ref update with `force=false`). That is the same CAS
anchor (parent commit / blob SHA) without putting a 1.5 MB payload through
Contents PUT.

Subcommands:
  preflight  Ensure the data-branch ref exists, fetch the blob, sanitize known
             derived item fields, validate, print JSON status.
  commit     Replace the ledger file with --file and fast-forward the ref.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pr_lifecycle_config import validate_bootstrap_pointer, validate_config
from pr_lifecycle_persist import sanitize_ledger_file
from pr_lifecycle_support import ROOT, SHA_RE
from pr_lifecycle_validation import validate
from pr_lifecycle_yaml import load_yaml

OWNER = "abhimehro"
REPO = "personal-config"
API_VERSION = "2022-11-28"
USER_AGENT = "pr-lifecycle-ledger-cas"
GITHUB_API_ORIGIN = "https://api.github.com"
DEFAULT_COMMIT_MESSAGE = "automated lifecycle ledger update"
OPERATOR_ERROR = "PR_LIFECYCLE_CAS_ERROR"
OPERATOR_CONFLICT = "PR_LIFECYCLE_CAS_CONFLICT"


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


def pointer_runtime() -> dict[str, Any]:
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    pointer = load_yaml(ROOT / "tasks/pr-lifecycle-ledger.yaml")
    validate_bootstrap_pointer(pointer, config)
    runtime = pointer["runtime_ledger"]
    if not isinstance(runtime, dict):
        raise ValueError("ledger pointer: runtime_ledger must be a mapping")
    return runtime


def github_token() -> str:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise CasError()
    return token


def github_api_url(path: str) -> str:
    """SECURITY: only the GitHub API origin; path must be a rooted API route."""
    if not path.startswith("/"):
        raise CasError()
    return f"{GITHUB_API_ORIGIN}{path}"


def github_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> Any:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        github_api_url(path),
        data=payload,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {github_token()}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw_body = response.read()
    except urllib.error.HTTPError as exc:
        exc.read()
        raise CasError(http_code=exc.code) from None
    if not raw_body:
        return {}
    parsed: Any = json.loads(raw_body.decode("utf-8"))
    return parsed


def ref_path(branch: str) -> str:
    """GET a single ref. GitHub uses the singular `/git/ref/` collection here."""
    return f"/repos/{OWNER}/{REPO}/git/ref/heads/{branch}"


def update_ref_path(branch: str) -> str:
    """PATCH a ref. GitHub uses the plural `/git/refs/` collection here."""
    return f"/repos/{OWNER}/{REPO}/git/refs/heads/{branch}"


def require_sha(value: Any) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise CasError()
    return value


def object_sha(payload: dict[str, Any]) -> str:
    object_payload = payload.get("object")
    if not isinstance(object_payload, dict):
        raise CasError()
    return require_sha(object_payload.get("sha"))


def tree_sha(commit: dict[str, Any]) -> str:
    tree_payload = commit.get("tree")
    if not isinstance(tree_payload, dict):
        raise CasError()
    return require_sha(tree_payload.get("sha"))


def optional_object_sha(ref: Any) -> str:
    if not isinstance(ref, dict):
        return ""
    object_payload = ref.get("object")
    if not isinstance(object_payload, dict):
        return ""
    sha = object_payload.get("sha")
    if isinstance(sha, str):
        return sha
    return ""


def is_stale_tip_error(exc: CasError) -> bool:
    return exc.http_code in {409, 422}


def contained_output_path(raw: Path) -> Path:
    """SECURITY: write only under the repo or the process temp workspace."""
    expanded = raw.expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    if expanded.exists() and expanded.is_symlink():
        raise CasError()
    resolved = expanded.resolve()
    allowed = (ROOT.resolve(), Path(tempfile.gettempdir()).resolve())
    for root in allowed:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise CasError()


def read_ref(branch: str) -> dict[str, Any] | None:
    try:
        payload = github_request("GET", ref_path(branch))
    except CasError as exc:
        if exc.http_code == 404:
            return None
        raise
    if not isinstance(payload, dict):
        raise CasError()
    return payload


def restore_ref(branch: str, sha: str) -> dict[str, Any]:
    require_sha(sha)
    created = github_request(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/refs",
        {"ref": f"refs/heads/{branch}", "sha": sha},
    )
    if not isinstance(created, dict):
        raise CasError()
    return created


def ensure_data_ref(runtime: dict[str, Any]) -> dict[str, Any]:
    branch = str(runtime["data_branch"])
    current = read_ref(branch)
    if current is not None:
        return {"restored": False, "ref": current}
    sha = runtime.get("last_known_data_commit")
    if not isinstance(sha, str) or not sha:
        raise CasError()
    restored = restore_ref(branch, sha)
    return {"restored": True, "ref": restored}


def contents_metadata(runtime: dict[str, Any], branch: str) -> dict[str, Any]:
    path = str(runtime["data_path"])
    payload = github_request(
        "GET",
        f"/repos/{OWNER}/{REPO}/contents/{path}?ref={branch}",
    )
    if not isinstance(payload, dict):
        raise CasError()
    require_sha(payload.get("sha"))
    return payload


def decode_github_blob(payload: dict[str, Any]) -> str:
    encoding = payload.get("encoding")
    content = payload.get("content")
    if encoding != "base64" or not isinstance(content, str) or not content:
        raise CasError()
    return base64.b64decode(content.encode("ascii")).decode("utf-8")


def fetch_blob_text(blob_sha: str) -> str:
    payload = github_request("GET", f"/repos/{OWNER}/{REPO}/git/blobs/{blob_sha}")
    if not isinstance(payload, dict):
        raise CasError()
    return decode_github_blob(payload)


def fetch_runtime_ledger(runtime: dict[str, Any], dest: Path) -> dict[str, Any]:
    dest = contained_output_path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    ensured = ensure_data_ref(runtime)
    branch = str(runtime["data_branch"])
    meta = contents_metadata(runtime, branch)
    dest.write_text(fetch_blob_text(str(meta["sha"])), encoding="utf-8")
    return {
        "restored_ref": bool(ensured["restored"]),
        "commit_sha": optional_object_sha(ensured["ref"]),
        "blob_sha": meta["sha"],
        "size": meta.get("size"),
        "encoding": meta.get("encoding"),
        "path": str(dest),
    }


def create_blob(content: str) -> str:
    payload = github_request(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/blobs",
        {"content": content, "encoding": "utf-8"},
    )
    if not isinstance(payload, dict):
        raise CasError()
    return require_sha(payload.get("sha"))


def read_commit(sha: str) -> dict[str, Any]:
    payload = github_request("GET", f"/repos/{OWNER}/{REPO}/git/commits/{sha}")
    if not isinstance(payload, dict):
        raise CasError()
    return payload


def create_tree(base_tree: str, path: str, blob_sha: str) -> str:
    payload = github_request(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/trees",
        {
            "base_tree": base_tree,
            "tree": [
                {
                    "path": path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha,
                }
            ],
        },
    )
    if not isinstance(payload, dict):
        raise CasError()
    return require_sha(payload.get("sha"))


def create_commit(message: str, tree_sha_value: str, parent_sha: str) -> str:
    payload = github_request(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/commits",
        {"message": message, "tree": tree_sha_value, "parents": [parent_sha]},
    )
    if not isinstance(payload, dict):
        raise CasError()
    return require_sha(payload.get("sha"))


def update_ref(branch: str, sha: str) -> dict[str, Any]:
    payload = github_request(
        "PATCH",
        update_ref_path(branch),
        {"sha": sha, "force": False},
    )
    if not isinstance(payload, dict):
        raise CasError()
    return payload


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
    try:
        update_ref(branch, commit_sha)
    except CasError as exc:
        if is_stale_tip_error(exc):
            raise CasError(OPERATOR_CONFLICT, http_code=exc.http_code) from None
        raise
    return {
        "commit_sha": commit_sha,
        "blob_sha": blob_sha,
        "parent_sha": parent_sha,
        "restored_ref": bool(ensured["restored"]),
        "attempt": 1,
    }


def run_preflight(out: Path) -> dict[str, Any]:
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
    runtime = pointer_runtime()
    contained = contained_output_path(file_path)
    # Always line-strip before validate+upload so projection keys cannot re-persist.
    sanitize_ledger_file(contained, bump_revision=bump_revision)
    stripped = validate(contained)
    content = contained.read_text(encoding="utf-8")
    result = cas_commit(runtime, content, message)
    result["validator_stripped_fields"] = stripped
    return result


def build_parser() -> argparse.ArgumentParser:
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
    if isinstance(exc, CasError):
        print(exc.code, file=sys.stderr)
    else:
        print(OPERATOR_ERROR, file=sys.stderr)
    if debug:
        http_code = getattr(exc, "http_code", None)
        print(f"{type(exc).__name__} http_code={http_code}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            status = run_preflight(args.out)
            print(json.dumps(status, indent=2))
            return 0
        result = run_commit(args.file, args.message, bump_revision=args.bump_revision)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        _print_operator_error(exc, debug=args.debug)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
