"""Git Data API helpers for CAS; callers inject the HTTP request callable."""

# Tests patch ``pr_lifecycle_ledger_cas.github_request``; these helpers never
# import that module, so the callable is passed in.

from __future__ import annotations

import base64
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pr_lifecycle_github_http import CasError
from pr_lifecycle_support import ROOT, SHA_RE

OWNER = "abhimehro"
REPO = "personal-config"
GithubRequest = Callable[..., Any]


def ref_path(branch: str) -> str:
    """GET a single ref. GitHub uses the singular ``/git/ref/`` collection."""
    return f"/repos/{OWNER}/{REPO}/git/ref/heads/{branch}"


def update_ref_path(branch: str) -> str:
    """PATCH a ref. GitHub uses the plural ``/git/refs/`` collection."""
    return f"/repos/{OWNER}/{REPO}/git/refs/heads/{branch}"


def require_sha(value: Any) -> str:
    """Return a 40-char hex SHA or fail closed."""
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise CasError()
    return value


def object_sha(payload: dict[str, Any]) -> str:
    """Read ``object.sha`` from a Git ref payload."""
    object_payload = payload.get("object")
    if not isinstance(object_payload, dict):
        raise CasError()
    return require_sha(object_payload.get("sha"))


def tree_sha(commit: dict[str, Any]) -> str:
    """Read ``tree.sha`` from a Git commit payload."""
    tree_payload = commit.get("tree")
    if not isinstance(tree_payload, dict):
        raise CasError()
    return require_sha(tree_payload.get("sha"))


def optional_object_sha(ref: Any) -> str:
    """Return ``object.sha`` when present; otherwise an empty string."""
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
    """Return whether GitHub rejected a fast-forward (409 or 422)."""
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


def decode_github_blob(payload: dict[str, Any]) -> str:
    """Decode a GitHub blob JSON body. Empty or non-base64 content fails closed."""
    encoding = payload.get("encoding")
    content = payload.get("content")
    if encoding != "base64":
        raise CasError()
    if not isinstance(content, str):
        raise CasError()
    if not content:
        raise CasError()
    return base64.b64decode(content.encode("ascii")).decode("utf-8")


def read_ref(branch: str, request: GithubRequest) -> dict[str, Any] | None:
    """GET a branch ref. Missing refs return None instead of raising."""
    try:
        payload = request("GET", ref_path(branch))
    except CasError as exc:
        if exc.http_code == 404:
            return None
        raise
    if not isinstance(payload, dict):
        raise CasError()
    return payload


def restore_ref(branch: str, sha: str, request: GithubRequest) -> dict[str, Any]:
    """POST ``refs/heads/<branch>`` at a recorded commit SHA."""
    require_sha(sha)
    created = request(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/refs",
        {"ref": f"refs/heads/{branch}", "sha": sha},
    )
    if not isinstance(created, dict):
        raise CasError()
    return created


def ensure_data_ref(runtime: dict[str, Any], request: GithubRequest) -> dict[str, Any]:
    """Create the data-branch ref from last_known_data_commit when GitHub 404s."""
    branch = str(runtime["data_branch"])
    current = read_ref(branch, request)
    if current is not None:
        return {"restored": False, "ref": current}
    sha = runtime.get("last_known_data_commit")
    if not isinstance(sha, str) or not sha:
        raise CasError()
    restored = restore_ref(branch, sha, request)
    return {"restored": True, "ref": restored}


def contents_metadata(
    runtime: dict[str, Any],
    branch: str,
    request: GithubRequest,
) -> dict[str, Any]:
    """GET Contents metadata for the ledger path (blob SHA, not file bytes)."""
    path = str(runtime["data_path"])
    payload = request(
        "GET",
        f"/repos/{OWNER}/{REPO}/contents/{path}?ref={branch}",
    )
    if not isinstance(payload, dict):
        raise CasError()
    require_sha(payload.get("sha"))
    return payload


def fetch_blob_text(blob_sha: str, request: GithubRequest) -> str:
    """GET and decode a Git blob. Contents GET is empty above 1 MB."""
    payload = request("GET", f"/repos/{OWNER}/{REPO}/git/blobs/{blob_sha}")
    if not isinstance(payload, dict):
        raise CasError()
    return decode_github_blob(payload)


def fetch_runtime_ledger(
    runtime: dict[str, Any],
    dest: Path,
    request: GithubRequest,
) -> dict[str, Any]:
    """Write the runtime ledger blob to a contained dest path."""
    dest = contained_output_path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    ensured = ensure_data_ref(runtime, request)
    branch = str(runtime["data_branch"])
    meta = contents_metadata(runtime, branch, request)
    dest.write_text(fetch_blob_text(str(meta["sha"]), request), encoding="utf-8")
    return {
        "restored_ref": bool(ensured["restored"]),
        "commit_sha": optional_object_sha(ensured["ref"]),
        "blob_sha": meta["sha"],
        "size": meta.get("size"),
        "encoding": meta.get("encoding"),
        "path": str(dest),
    }


def create_blob(content: str, request: GithubRequest) -> str:
    """POST a utf-8 Git blob and return its SHA."""
    payload = request(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/blobs",
        {"content": content, "encoding": "utf-8"},
    )
    if not isinstance(payload, dict):
        raise CasError()
    return require_sha(payload.get("sha"))


def read_commit(sha: str, request: GithubRequest) -> dict[str, Any]:
    """GET a Git commit object."""
    payload = request("GET", f"/repos/{OWNER}/{REPO}/git/commits/{sha}")
    if not isinstance(payload, dict):
        raise CasError()
    return payload


def create_tree(
    base_tree: str,
    path: str,
    blob_sha: str,
    request: GithubRequest,
) -> str:
    """POST a tree that replaces one path on top of ``base_tree``."""
    payload = request(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/trees",
        {
            "base_tree": base_tree,
            "tree": [
                {"path": path, "mode": "100644", "type": "blob", "sha": blob_sha},
            ],
        },
    )
    if not isinstance(payload, dict):
        raise CasError()
    return require_sha(payload.get("sha"))


def create_commit(
    message: str,
    tree_sha_value: str,
    parent_sha: str,
    request: GithubRequest,
) -> str:
    """POST a commit with a single parent (fast-forward CAS)."""
    payload = request(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/commits",
        {"message": message, "tree": tree_sha_value, "parents": [parent_sha]},
    )
    if not isinstance(payload, dict):
        raise CasError()
    return require_sha(payload.get("sha"))


def update_ref(
    branch: str,
    sha: str,
    request: GithubRequest,
    expected_sha: str | None = None,
) -> dict[str, Any]:
    """PATCH a branch ref with ``force=false`` so stale tips 409/422."""
    body: dict[str, object] = {"sha": sha, "force": False}
    if expected_sha is not None:
        body["expected_sha"] = expected_sha
    payload = request("PATCH", update_ref_path(branch), body)
    if not isinstance(payload, dict):
        raise CasError()
    return payload
