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
import time
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
MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 2.0


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
        raise ValueError("GH_TOKEN or GITHUB_TOKEN is required for ledger CAS")
    return token


def github_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> Any:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.github.com{path}",
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
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"GitHub {method} {path}: HTTP {exc.code}: {detail}") from exc
    if not raw_body:
        return {}
    parsed: Any = json.loads(raw_body.decode("utf-8"))
    return parsed


def ref_path(branch: str) -> str:
    return f"/repos/{OWNER}/{REPO}/git/ref/heads/{branch}"


def read_ref(branch: str) -> dict[str, Any] | None:
    try:
        payload = github_request("GET", ref_path(branch))
    except ValueError as exc:
        if "HTTP 404" in str(exc):
            return None
        raise
    if not isinstance(payload, dict):
        raise ValueError(f"git ref {branch}: expected mapping")
    return payload


def restore_ref(branch: str, sha: str) -> dict[str, Any]:
    if not SHA_RE.fullmatch(sha):
        raise ValueError("last_known_data_commit: expected 40-char lowercase SHA")
    created = github_request(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/refs",
        {"ref": f"refs/heads/{branch}", "sha": sha},
    )
    if not isinstance(created, dict):
        raise ValueError("git ref restore: expected mapping")
    return created


def ensure_data_ref(runtime: dict[str, Any]) -> dict[str, Any]:
    branch = str(runtime["data_branch"])
    current = read_ref(branch)
    if current is not None:
        return {"restored": False, "ref": current}
    sha = runtime.get("last_known_data_commit")
    if not isinstance(sha, str) or not sha:
        raise ValueError(
            f"git ref heads/{branch} is missing and last_known_data_commit is unset"
        )
    restored = restore_ref(branch, sha)
    return {"restored": True, "ref": restored}


def contents_metadata(runtime: dict[str, Any], branch: str) -> dict[str, Any]:
    path = str(runtime["data_path"])
    payload = github_request(
        "GET",
        f"/repos/{OWNER}/{REPO}/contents/{path}?ref={branch}",
    )
    if not isinstance(payload, dict):
        raise ValueError("contents metadata: expected mapping")
    sha = payload.get("sha")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ValueError("contents metadata: missing blob SHA")
    return payload


def fetch_blob_text(blob_sha: str) -> str:
    payload = github_request("GET", f"/repos/{OWNER}/{REPO}/git/blobs/{blob_sha}")
    if not isinstance(payload, dict):
        raise ValueError("git blob: expected mapping")
    content = payload.get("content")
    encoding = payload.get("encoding")
    if encoding != "base64" or not isinstance(content, str) or not content:
        raise ValueError("git blob: expected base64 content")
    return base64.b64decode(content.encode("ascii")).decode("utf-8")


def fetch_runtime_ledger(runtime: dict[str, Any], dest: Path) -> dict[str, Any]:
    ensured = ensure_data_ref(runtime)
    branch = str(runtime["data_branch"])
    meta = contents_metadata(runtime, branch)
    dest.write_text(fetch_blob_text(str(meta["sha"])), encoding="utf-8")
    object_payload = ensured["ref"].get("object") if isinstance(ensured["ref"], dict) else None
    commit_sha = ""
    if isinstance(object_payload, dict) and isinstance(object_payload.get("sha"), str):
        commit_sha = object_payload["sha"]
    return {
        "restored_ref": bool(ensured["restored"]),
        "commit_sha": commit_sha,
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
    if not isinstance(payload, dict) or not isinstance(payload.get("sha"), str):
        raise ValueError("git blob create: missing sha")
    sha = payload["sha"]
    if not SHA_RE.fullmatch(sha):
        raise ValueError("git blob create: invalid sha")
    return sha


def read_commit(sha: str) -> dict[str, Any]:
    payload = github_request("GET", f"/repos/{OWNER}/{REPO}/git/commits/{sha}")
    if not isinstance(payload, dict):
        raise ValueError("git commit: expected mapping")
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
    if not isinstance(payload, dict) or not isinstance(payload.get("sha"), str):
        raise ValueError("git tree create: missing sha")
    sha = payload["sha"]
    if not SHA_RE.fullmatch(sha):
        raise ValueError("git tree create: invalid sha")
    return sha


def create_commit(message: str, tree_sha: str, parent_sha: str) -> str:
    payload = github_request(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/commits",
        {"message": message, "tree": tree_sha, "parents": [parent_sha]},
    )
    if not isinstance(payload, dict) or not isinstance(payload.get("sha"), str):
        raise ValueError("git commit create: missing sha")
    sha = payload["sha"]
    if not SHA_RE.fullmatch(sha):
        raise ValueError("git commit create: invalid sha")
    return sha


def update_ref(branch: str, sha: str) -> dict[str, Any]:
    payload = github_request(
        "PATCH",
        ref_path(branch),
        {"sha": sha, "force": False},
    )
    if not isinstance(payload, dict):
        raise ValueError("git ref update: expected mapping")
    return payload


def cas_commit(runtime: dict[str, Any], content: str, message: str) -> dict[str, Any]:
    """Fast-forward the data branch. Retry once on a stale tip."""
    branch = str(runtime["data_branch"])
    path = str(runtime["data_path"])
    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        ensured = ensure_data_ref(runtime)
        ref = ensured["ref"]
        object_payload = ref.get("object") if isinstance(ref, dict) else None
        if not isinstance(object_payload, dict) or not isinstance(
            object_payload.get("sha"), str
        ):
            raise ValueError("git ref: missing object sha")
        parent_sha = object_payload["sha"]
        parent = read_commit(parent_sha)
        tree_payload = parent.get("tree")
        if not isinstance(tree_payload, dict) or not isinstance(tree_payload.get("sha"), str):
            raise ValueError("git commit: missing tree sha")
        blob_sha = create_blob(content)
        tree_sha = create_tree(tree_payload["sha"], path, blob_sha)
        commit_sha = create_commit(message, tree_sha, parent_sha)
        try:
            update_ref(branch, commit_sha)
        except ValueError as exc:
            last_error = str(exc)
            if attempt < MAX_ATTEMPTS and (
                "not a fast forward" in last_error.lower()
                or "HTTP 422" in last_error
            ):
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            raise
        return {
            "commit_sha": commit_sha,
            "blob_sha": blob_sha,
            "parent_sha": parent_sha,
            "restored_ref": bool(ensured["restored"]),
            "attempt": attempt,
        }
    raise ValueError(f"ledger CAS failed after retry: {last_error}")


def run_preflight(out: Path) -> dict[str, Any]:
    runtime = pointer_runtime()
    fetch = fetch_runtime_ledger(runtime, out)
    sanitized = sanitize_ledger_file(out, bump_revision=False)
    stripped = validate(out)
    status = {
        "ok": True,
        "ref_restored": fetch["restored_ref"],
        "commit_sha": fetch["commit_sha"],
        "blob_sha": fetch["blob_sha"],
        "size": fetch["size"],
        "contents_encoding": fetch["encoding"],
        "sanitized_fields": sanitized["removed_fields"],
        "validator_stripped_fields": stripped,
        "ledger_path": str(out),
    }
    return status


def run_commit(file_path: Path, message: str, *, bump_revision: bool) -> dict[str, Any]:
    runtime = pointer_runtime()
    if bump_revision:
        sanitize_ledger_file(file_path, bump_revision=True)
    stripped = validate(file_path)
    content = file_path.read_text(encoding="utf-8")
    result = cas_commit(runtime, content, message)
    result["validator_stripped_fields"] = stripped
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--out", type=Path, required=True)
    commit = sub.add_parser("commit")
    commit.add_argument("--file", type=Path, required=True)
    commit.add_argument("--message", required=True)
    commit.add_argument("--bump-revision", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "preflight":
            status = run_preflight(args.out)
            print(json.dumps(status, indent=2))
            return 0
        result = run_commit(args.file, args.message, bump_revision=args.bump_revision)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PR_LIFECYCLE_CAS_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
