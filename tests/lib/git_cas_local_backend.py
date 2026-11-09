"""Local git repo that implements the Git Data paths CAS tests need."""

from __future__ import annotations

import base64
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pr_lifecycle_github_http import OPERATOR_CONFLICT, CasError

OWNER = "abhimehro"
REPO = "personal-config"


def _git(repo: Path, *args: str, input_text: str | None = None) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=input_text,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


class LocalGitCasBackend:
    """In-process git objects backing a minimal GitHub Git Data API surface."""

    def __init__(self, branch: str = "automation/pr-lifecycle-ledger") -> None:
        self.branch = branch
        self.data_path = "pr-lifecycle-ledger.yaml"
        self._tmpdir = tempfile.TemporaryDirectory(prefix="ledger-cas-git-")
        self.repo = Path(self._tmpdir.name)
        _git(self.repo, "init", "-b", branch)
        _git(self.repo, "config", "user.email", "cas-test@example.com")
        _git(self.repo, "config", "user.name", "cas-test")

    def cleanup(self) -> None:
        self._tmpdir.cleanup()

    def seed_ledger(self, text: str) -> str:
        """Write initial ledger content; return the tip commit SHA."""
        blob = _git(self.repo, "hash-object", "-w", "--stdin", input_text=text)
        tree = _git(
            self.repo,
            "mktree",
            input_text=f"100644 blob {blob}\t{self.data_path}\n",
        )
        commit = _git(
            self.repo,
            "commit-tree",
            tree,
            "-m",
            "seed ledger",
        )
        _git(self.repo, "update-ref", f"refs/heads/{self.branch}", commit)
        return commit

    def tip(self) -> str:
        return _git(self.repo, "rev-parse", f"refs/heads/{self.branch}")

    def ledger_bytes_at_tip(self) -> str:
        commit = self.tip()
        tree = _git(self.repo, "rev-parse", f"{commit}^{{tree}}")
        entries = _git(self.repo, "ls-tree", tree).splitlines()
        for line in entries:
            parts = line.split()
            if len(parts) >= 4 and parts[3] == self.data_path:
                blob = parts[2]
                return _git(self.repo, "cat-file", "-p", blob)
        raise CasError()

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        if method == "GET" and path.endswith(f"/git/ref/heads/{self.branch}"):
            sha = self.tip()
            return {"ref": f"refs/heads/{self.branch}", "object": {"sha": sha, "type": "commit"}}
        if method == "GET" and f"/contents/{self.data_path}" in path:
            commit = self.tip()
            tree = _git(self.repo, "rev-parse", f"{commit}^{{tree}}")
            blob = None
            for line in _git(self.repo, "ls-tree", tree).splitlines():
                parts = line.split()
                if len(parts) >= 4 and parts[3] == self.data_path:
                    blob = parts[2]
                    break
            if blob is None:
                raise CasError(http_code=404)
            size = int(_git(self.repo, "cat-file", "-s", blob))
            return {"sha": blob, "size": size, "encoding": "base64", "content": ""}
        if method == "GET" and "/git/blobs/" in path:
            blob = path.rsplit("/", 1)[-1]
            raw = _git(self.repo, "cat-file", "-p", blob)
            encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
            return {"encoding": "base64", "content": encoded, "sha": blob}
        if method == "GET" and "/git/commits/" in path:
            sha = path.rsplit("/", 1)[-1]
            return {"sha": sha, "tree": {"sha": _git(self.repo, "rev-parse", f"{sha}^{{tree}}")}}
        if method == "POST" and path.endswith("/git/blobs"):
            assert body is not None
            content = str(body.get("content", ""))
            blob = _git(self.repo, "hash-object", "-w", "--stdin", input_text=content)
            return {"sha": blob}
        if method == "POST" and path.endswith("/git/trees"):
            assert body is not None
            base_tree = str(body["base_tree"])
            entry = body["tree"][0]
            rel_path = str(entry["path"])
            blob = str(entry["sha"])
            mode = str(entry.get("mode", "100644"))
            typ = str(entry.get("type", "blob"))
            lines: list[str] = []
            replaced = False
            for line in _git(self.repo, "ls-tree", base_tree).splitlines():
                parts = line.split(maxsplit=3)
                if len(parts) >= 4 and parts[3] == rel_path:
                    lines.append(f"{mode} {typ} {blob}\t{rel_path}\n")
                    replaced = True
                else:
                    entry_mode, entry_type, entry_sha, name = parts
                    mode_digits = entry_mode[3:] if entry_mode.startswith("0") else entry_mode
                    lines.append(f"{mode_digits} {entry_type} {entry_sha}\t{name}\n")
            if not replaced:
                lines.append(f"{mode} {typ} {blob}\t{rel_path}\n")
            new_tree = _git(self.repo, "mktree", input_text="".join(lines))
            return {"sha": new_tree}
        if method == "POST" and path.endswith("/git/commits"):
            assert body is not None
            tree = str(body["tree"])
            parent = str(body["parents"][0])
            message = str(body.get("message", "update"))
            commit = _git(self.repo, "commit-tree", tree, "-p", parent, "-m", message)
            return {"sha": commit}
        if method == "PATCH" and f"/git/refs/heads/{self.branch}" in path:
            assert body is not None
            new_sha = str(body["sha"])
            expected = body.get("expected_sha")
            current = self.tip()
            if expected is not None and str(expected) != current:
                raise CasError(OPERATOR_CONFLICT, http_code=422)
            if expected is not None:
                _git(
                    self.repo,
                    "update-ref",
                    f"refs/heads/{self.branch}",
                    new_sha,
                    str(expected),
                )
            else:
                _git(self.repo, "update-ref", f"refs/heads/{self.branch}", new_sha)
            return {"ref": f"refs/heads/{self.branch}", "object": {"sha": new_sha}}
        raise AssertionError((method, path, body))
