#!/usr/bin/env python3
"""Antigravity PreToolUse defense-in-depth safety guard for proactive workflows.

Reads Antigravity camelCase protojson hook input from stdin and outputs a JSON
decision (`allow` or `deny`). Server-side GitHub rulesets and non-bypass tokens
remain the authoritative remote boundary; this hook acts as a fast local guard
against force pushes, unmerged public `.jules/sentinel.md` writes, public
Sentinel Draft PRs, and primary-checkout edits or remote mutations during
proactive sweep sessions.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
import time
from pathlib import Path
from typing import Any

PROACTIVE_PREFIX = "[PROACTIVE-SWEEP]"
SENTINEL_PR_RE = re.compile(r"\b(?:sentinel|cwe-\d+|vulnerability)\b", re.IGNORECASE)
GH_MUTATE_RE = re.compile(
    r"(?:^|[;&|()\s`])gh\s+(?:pr\s+(?:create|merge|ready|close|review|edit)|issue\s+create|api\b[^\n]*\s(?:-X|--method)\s*(?:POST|PUT|PATCH|DELETE))",
    re.IGNORECASE,
)
GH_PR_CREATE_RE = re.compile(r"(?:^|[;&|()\s`])gh\s+pr\s+create\b", re.IGNORECASE)
GH_MERGE_RE = re.compile(r"(?:^|[;&|()\s`])gh\s+pr\s+merge\b", re.IGNORECASE)
SENTINEL_CMD_RE = re.compile(r"\.jules/sentinel\.md\b")


def _home_dir() -> Path:
    return Path(os.environ.get("HOME") or str(Path.home()))


def _reports_dir() -> Path:
    return _home_dir() / ".gemini" / "antigravity" / "proactive-reports"


def _worktrees_dir() -> Path:
    return _home_dir() / ".gemini" / "antigravity" / "worktrees"


def _dev_root() -> Path:
    return _home_dir() / "dev"


def _emit(decision: str, reason: str = "") -> int:
    out: dict[str, str] = {"decision": decision}
    if reason:
        out["reason"] = reason
    sys.stdout.write(json.dumps(out) + "\n")
    return 0


def _load_json_dict(path: Path) -> dict[str, Any]:
    """Read a JSON object, returning {} for a missing file, I/O error, or invalid JSON.

    Non-object JSON also returns {}. Invalid UTF-8 raises UnicodeDecodeError.
    """
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_private_json(path: Path, data: dict[str, Any]) -> None:
    """Replace a JSON file with a private copy, ignoring filesystem errors.

    Serialization errors propagate to the caller.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        tmp_path = path.parent / f".tmp.{path.name}.{os.getpid()}.{time.time_ns()}"
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with open(fd, "w", encoding="utf-8", closefd=False) as f:
                f.write(json.dumps(data, indent=2) + "\n")
                f.flush()
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp_path, path)
    except OSError:
        pass


def _is_proactive_session(payload: dict[str, Any]) -> bool:
    """Detect a sweep using the environment, workspace, prompt, or conversation registry.

    A matching workspace or prompt records the conversation ID when present;
    registry entries remain active for 24 hours after their recorded timestamp.
    """
    if os.environ.get("AGY_PROACTIVE_SESSION") == "1":
        return True

    conv_id = str(payload.get("conversationId") or "").strip()
    reg_path = _reports_dir() / ".sweep-conversations.json"
    reg = _load_json_dict(reg_path)
    now = time.time()
    active_convs = {
        k: v
        for k, v in reg.items()
        if isinstance(v, (int, float)) and now - float(v) < 86400
    }

    wt_resolved = _worktrees_dir().resolve(strict=False)
    ws_paths = payload.get("workspacePaths")
    in_wt_workspace = False
    if isinstance(ws_paths, list):
        for raw_ws in ws_paths:
            if not isinstance(raw_ws, str) or not raw_ws.strip():
                continue
            cleaned = raw_ws.removeprefix("file://")
            try:
                resolved_ws = Path(cleaned).expanduser().resolve(strict=False)
                if resolved_ws == wt_resolved or wt_resolved in resolved_ws.parents:
                    in_wt_workspace = True
                    break
            except OSError:
                continue

    last_input = str(payload.get("lastUserInput") or "").lstrip()
    starts_with_marker = last_input.startswith(PROACTIVE_PREFIX)

    if in_wt_workspace or starts_with_marker:
        if conv_id:
            active_convs[conv_id] = now
            _save_private_json(reg_path, active_convs)
        return True

    return bool(conv_id and conv_id in active_convs)


def _has_valid_sentinel_lease(
    target_hint: str, target_path: Path | None = None
) -> bool:
    """Check that an unexpired lease names the target repository.

    Match the sentinel file path when provided, otherwise match the repository
    in the command hint. Invalid lease expiry values can raise TypeError or
    ValueError; invalid UTF-8 in the lease file raises UnicodeDecodeError.
    """
    lease_path = _reports_dir() / ".sentinel-post-merge-lease.json"
    lease = _load_json_dict(lease_path)
    expires_at = float(lease.get("expires_at") or 0.0)
    repo_name = str(lease.get("repo_name") or "").strip()
    if not repo_name or time.time() >= expires_at:
        return False
    if target_path is not None:
        parts = target_path.expanduser().parts
        return (
            len(parts) >= 3
            and parts[-3] == repo_name
            and parts[-2] == ".jules"
            and parts[-1] == "sentinel.md"
        )
    pattern = rf"(?:/dev/|(?:^|\s)-C\s+[^;\n]*/){re.escape(repo_name)}(?=/|\s|$|[\"'])"
    return bool(re.search(pattern, target_hint))


def _iter_git_invocations(cmd: str) -> list[list[str]]:
    """Extract tokenized git invocations across command segments and shell -c wrappers."""
    invocations: list[list[str]] = []
    for segment in re.split(r"[;&|\n]+", cmd):
        try:
            tokens = shlex.split(segment, comments=True)
        except ValueError:
            tokens = segment.split()
        if not tokens:
            continue
        idx = 0
        while (
            idx < len(tokens) and "=" in tokens[idx] and not tokens[idx].startswith("-")
        ):
            idx += 1
        if idx >= len(tokens):
            continue
        base = os.path.basename(tokens[idx])
        if base in ("agent-zsh", "agent-bash", "bash", "zsh", "sh"):
            c_idx = next(
                (
                    i
                    for i in range(idx + 1, len(tokens))
                    if tokens[i].startswith("-")
                    and not tokens[i].startswith("--")
                    and "c" in tokens[i][1:]
                ),
                None,
            )
            if c_idx is not None and c_idx + 1 < len(tokens):
                invocations.extend(_iter_git_invocations(tokens[c_idx + 1]))
            continue
        if base == "git":
            invocations.append(tokens[idx + 1 :])
    return invocations


def _git_subcommand_and_args(git_args: list[str]) -> tuple[str, list[str], bool]:
    """Return (subcommand, remaining_args, has_push_alias) after global git flags."""
    has_push_alias = False
    i = 0
    opts_taking_val = {
        "-C",
        "-c",
        "--git-dir",
        "--work-tree",
        "--namespace",
        "--config-env",
    }
    while i < len(git_args):
        tok = git_args[i]
        if tok == "--":
            i += 1
            break
        if tok in opts_taking_val:
            if tok == "-c" and i + 1 < len(git_args):
                cfg = git_args[i + 1]
                if cfg.lower().startswith("alias.") and "push" in cfg.lower():
                    has_push_alias = True
            i += 2
            continue
        if any(tok.startswith(f"{opt}=") for opt in opts_taking_val):
            if (
                tok.lower().startswith("-c")
                and "alias." in tok.lower()
                and "push" in tok.lower()
            ):
                has_push_alias = True
            i += 1
            continue
        if tok.startswith("-"):
            i += 1
            continue
        return tok, git_args[i + 1 :], has_push_alias
    return "", [], has_push_alias


def _is_any_git_push(cmd: str) -> bool:
    """Detect any git push (named remote, explicit URL, -C <dir> push, or -c alias=push)."""
    for git_args in _iter_git_invocations(cmd):
        sub, _rest, has_push_alias = _git_subcommand_and_args(git_args)
        if sub == "push" or has_push_alias:
            return True
    return False


def _is_force_push_to_protected(cmd: str) -> bool:
    """Detect force pushes to protected branches and pushes with +refspecs.

    Force flags also match when there are at most two push arguments or a push
    alias is detected; +refspecs match regardless of the target branch.
    """
    for git_args in _iter_git_invocations(cmd):
        sub, rest, has_push_alias = _git_subcommand_and_args(git_args)
        if sub != "push" and not has_push_alias:
            continue
        has_force_flag = any(
            t in ("-f", "--force")
            or t.startswith("--force-with-lease")
            or t.startswith("--force-if-includes")
            for t in rest
        )
        has_plus_refspec = any(
            t.startswith("+") and len(t) > 1 and not t.startswith("+-") for t in rest
        )
        targets_protected = any(
            re.search(r"(?:^|:)(?:refs/heads/)?(?:main|master|trunk)$", t.lstrip("+"))
            for t in rest
        )
        if has_plus_refspec or (
            has_force_flag and (targets_protected or len(rest) <= 2)
        ):
            return True
        if has_push_alias and has_force_flag:
            return True
    return False


def _mutates_sentinel_in_shell(cmd: str) -> bool:
    """Check whether any shell line/segment writes, edits, copies, or stages .jules/sentinel.md."""
    for line in cmd.splitlines():
        if not SENTINEL_CMD_RE.search(line):
            continue
        if (
            any(
                op in line
                for op in (">", "tee ", "sed -i", "cp ", "mv ", "install ")
            )
            or re.search(r"\bgit\b[^\n]*\b(?:add|commit|checkout)\b", line)
        ):
            return True
    return False


def _check_file_target(path_str: str, is_proactive: bool) -> tuple[str, str] | None:
    """Return a denial and reason for restricted file targets, or None.

    Sentinel files require a matching lease; proactive sessions also block
    targets resolving under ~/dev. Lease parsing errors propagate.
    """
    if not path_str:
        return None
    if path_str.startswith("file://"):
        path_str = path_str[7:]
    norm = Path(path_str).expanduser()
    parts = norm.parts
    if len(parts) >= 2 and parts[-2] == ".jules" and parts[-1] == "sentinel.md":
        if not _has_valid_sentinel_lease(str(norm), target_path=norm):
            return (
                "deny",
                "Blocked pre-merge write to .jules/sentinel.md in a public repo. "
                "Write Sentinel findings to ~/.gemini/antigravity/proactive-reports/ "
                "and unlock post-merge updates via antigravity-proactive-ctl.sh sentinel-post-merge.",
            )
    if is_proactive:
        try:
            real_path = Path(os.path.realpath(str(norm)))
            dev_real = Path(os.path.realpath(str(_dev_root())))
            if real_path == dev_real or dev_real in real_path.parents:
                return (
                    "deny",
                    "Blocked direct edit to primary checkout under ~/dev during "
                    "proactive sweep. Edit inside the isolated worktree created by "
                    "proactive-worktree.sh instead.",
                )
        except OSError:
            pass
    return None


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return _emit("allow")
    try:
        payload: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        return _emit("allow")

    is_proactive = _is_proactive_session(payload)
    allow_draft_pr = os.environ.get("AGY_PROACTIVE_ALLOW_DRAFT_PR") == "1"

    tool_call = payload.get("toolCall")
    if not isinstance(tool_call, dict):
        return _emit("allow")

    tool_name = str(tool_call.get("name") or "")
    args = tool_call.get("args")
    if not isinstance(args, dict):
        args = {}

    if tool_name in (
        "write_file",
        "edit_file",
        "multi_edit_file",
        "replace_file_content",
    ):
        target_path = str(
            args.get("Path")
            or args.get("path")
            or args.get("TargetFile")
            or args.get("targetFile")
            or args.get("filePath")
            or args.get("file_path")
            or ""
        )
        verdict = _check_file_target(target_path, is_proactive)
        if verdict is not None:
            return _emit(verdict[0], verdict[1])
        return _emit("allow")

    if tool_name == "run_command":
        cmd = str(args.get("CommandLine") or args.get("command") or "")
        if _is_force_push_to_protected(cmd):
            return _emit(
                "deny",
                "Blocked force-push or +refspec push to protected branch.",
            )
        if _mutates_sentinel_in_shell(cmd) and not _has_valid_sentinel_lease(cmd):
            return _emit(
                "deny",
                "Blocked pre-merge modification/staging of .jules/sentinel.md.",
            )
        if GH_PR_CREATE_RE.search(cmd) and SENTINEL_PR_RE.search(cmd):
            return _emit(
                "deny",
                "Blocked public PR creation for Sentinel security finding; use GitHub Security Advisories or keep local-only.",
            )
        if is_proactive:
            if GH_MERGE_RE.search(cmd):
                return _emit(
                    "deny",
                    "Blocked autonomous PR merge during proactive sweep.",
                )
            if not allow_draft_pr and (
                _is_any_git_push(cmd) or GH_MUTATE_RE.search(cmd)
            ):
                return _emit(
                    "deny",
                    "Blocked remote push/PR mutation during local-only (2B) proactive pilot.",
                )
    return _emit("allow")


if __name__ == "__main__":
    raise SystemExit(main())
