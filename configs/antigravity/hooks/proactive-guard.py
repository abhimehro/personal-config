#!/usr/bin/env python3
# pylint: disable=invalid-name
"""Antigravity PreToolUse defense-in-depth safety guard for proactive workflows."""

from __future__ import annotations

import json
import os
import re
import shlex
import stat
import sys
import time
from pathlib import Path
from typing import Any

PROACTIVE_PREFIX = "[PROACTIVE-SWEEP]"
ONE_DAY_SECONDS = 86400
SENTINEL_PR_RE = re.compile(r"\b(?:sentinel|cwe-\d+|vulnerability)\b", re.IGNORECASE)
GH_MUTATE_RE = re.compile(
    r"(?:^|[;&|()\s`])gh\s+(?:"
    r"pr\s+(?:create|merge|ready|close|review|edit)"
    r"|issue\s+create"
    r"|api\b[^;&|\n]*\s(?:"
    r"(?:-X(?:\s*|=)|--method(?:\s+|=))(?:POST|PUT|PATCH|DELETE)\b"
    r"|(?:-f|-F|--(?:raw-)?field|--input)(?:[\s=]|$)"
    r")"
    r")",
    re.IGNORECASE,
)
GH_PR_CREATE_RE = re.compile(r"(?:^|[;&|()\s`])gh\s+pr\s+create\b", re.IGNORECASE)
GH_MERGE_RE = re.compile(r"(?:^|[;&|()\s`])gh\s+pr\s+merge\b", re.IGNORECASE)
SENTINEL_CMD_RE = re.compile(r"\.jules/sentinel\.md\b")
SENTINEL_GIT_CMD_RE = re.compile(r"\bgit\b[^\n]*\b(?:add|commit|checkout)\b")
PROTECTED_BRANCH_RE = re.compile(r"(?:^|:)(?:refs/heads/)?(?:main|master|trunk)$")

SHELL_WRAPPERS = frozenset({"agent-zsh", "agent-bash", "bash", "zsh", "sh"})
SHELL_SENTINEL_OPS = (">", "tee ", "sed -i", "cp ", "mv ", "install ")
GIT_OPTS_TAKING_VAL = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"}
)
FILE_TOOLS = frozenset(
    {"write_file", "edit_file", "multi_edit_file", "replace_file_content"}
)


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


def _emit_verdict(verdict: tuple[str, str] | None) -> int:
    if verdict is None:
        return _emit("allow")
    return _emit(verdict[0], verdict[1])


def _load_json_dict(path: Path) -> dict[str, Any]:
    """Read a JSON object, returning {} for a missing file, I/O error, or invalid JSON."""
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_private_json(path: Path, data: dict[str, Any]) -> None:
    """Replace a JSON file atomically with 0600/0700 permissions, ignoring OSError."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.parent.chmod(stat.S_IRWXU)
        tmp_path = path.parent / f".tmp.{path.name}.{os.getpid()}.{time.time_ns()}"
        tmp_fd = os.open(
            tmp_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            stat.S_IRUSR | stat.S_IWUSR,
        )
        try:
            with open(tmp_fd, "w", encoding="utf-8", closefd=False) as tmp_file:
                tmp_file.write(json.dumps(data, indent=2) + "\n")
                tmp_file.flush()
            os.fsync(tmp_fd)
        finally:
            os.close(tmp_fd)
        os.replace(tmp_path, path)
    except OSError:
        pass


def _prune_active_conversations(reg: dict[str, Any], now: float) -> dict[str, Any]:
    """Return conversation registry entries newer than 24 hours."""
    return {
        conv: ts
        for conv, ts in reg.items()
        if isinstance(ts, (int, float)) and now - float(ts) < ONE_DAY_SECONDS
    }


def _is_path_under_root(raw_ws: Any, root: Path) -> bool:
    """Return True when a workspace entry resolves inside or equal to root."""
    if not isinstance(raw_ws, str) or not raw_ws.strip():
        return False
    cleaned = raw_ws.removeprefix("file://")
    try:
        resolved_ws = Path(cleaned).expanduser().resolve(strict=False)
    except OSError:
        return False
    return resolved_ws == root or root in resolved_ws.parents


def _has_worktree_workspace(payload: dict[str, Any]) -> bool:
    """Return True when any payload workspacePath lives under the worktrees root."""
    ws_paths = payload.get("workspacePaths")
    if not isinstance(ws_paths, list):
        return False
    wt_resolved = _worktrees_dir().resolve(strict=False)
    return any(_is_path_under_root(raw_ws, wt_resolved) for raw_ws in ws_paths)


def _starts_with_proactive_prefix(payload: dict[str, Any]) -> bool:
    """Return True when lastUserInput begins with the proactive sweep marker."""
    last_input = str(payload.get("lastUserInput") or "").lstrip()
    return last_input.startswith(PROACTIVE_PREFIX)


def _record_proactive_conversation(
    reg_path: Path, active_convs: dict[str, Any], conv_id: str, now: float
) -> None:
    """Persist conv_id in the 24-hour active sweep conversation registry."""
    if conv_id:
        active_convs[conv_id] = now
        _save_private_json(reg_path, active_convs)


def _is_proactive_session(payload: dict[str, Any]) -> bool:
    """Detect a sweep using the environment, workspace, prompt, or 24h conversation registry."""
    if os.environ.get("AGY_PROACTIVE_SESSION") == "1":
        return True

    conv_id = str(payload.get("conversationId") or "").strip()
    reg_path = _reports_dir() / ".sweep-conversations.json"
    now = time.time()
    active_convs = _prune_active_conversations(_load_json_dict(reg_path), now)

    if _has_worktree_workspace(payload) or _starts_with_proactive_prefix(payload):
        _record_proactive_conversation(reg_path, active_convs, conv_id, now)
        return True

    return bool(conv_id and conv_id in active_convs)


def _is_repo_sentinel_path(target_path: Path, repo_name: str) -> bool:
    """Return True when target_path points to <repo_name>/.jules/sentinel.md."""
    parts = target_path.expanduser().parts
    return len(parts) >= 3 and parts[-3:] == (repo_name, ".jules", "sentinel.md")


def _has_valid_sentinel_lease(
    target_hint: str, target_path: Path | None = None
) -> bool:
    """Check that an unexpired lease names the target repository or sentinel path."""
    lease_path = _reports_dir() / ".sentinel-post-merge-lease.json"
    lease = _load_json_dict(lease_path)
    expires_at = float(lease.get("expires_at") or 0.0)
    repo_name = str(lease.get("repo_name") or "").strip()
    if not repo_name or time.time() >= expires_at:
        return False
    if target_path is not None:
        return _is_repo_sentinel_path(target_path, repo_name)
    pattern = rf"(?:/dev/|(?:^|\s)-C\s+[^;\n]*/){re.escape(repo_name)}(?=/|\s|$|[\"'])"
    return bool(re.search(pattern, target_hint))


def _tokenize_segment(segment: str) -> list[str]:
    """Split a command segment using shlex, falling back to whitespace split."""
    try:
        return shlex.split(segment, comments=True)
    except ValueError:
        return segment.split()


def _is_env_assignment(token: str) -> bool:
    """Return True when token is a VAR=value shell assignment."""
    return "=" in token and not token.startswith("-")


def _strip_leading_env_vars(tokens: list[str]) -> list[str]:
    """Drop leading VAR=val assignments from a tokenized shell command."""
    for idx, token in enumerate(tokens):
        if not _is_env_assignment(token):
            return tokens[idx:]
    return []


def _is_short_c_flag(token: str) -> bool:
    """Return True for short option clusters containing -c (excluding --long)."""
    return token.startswith("-") and not token.startswith("--") and "c" in token[1:]


def _find_shell_command_arg(tokens: list[str]) -> str | None:
    """Extract the inline script argument following a shell -c option cluster."""
    for idx in range(1, len(tokens) - 1):
        if _is_short_c_flag(tokens[idx]):
            return tokens[idx + 1]
    return None


def _collect_segment_git_invocations(segment: str) -> list[list[str]]:
    """Return tokenized git invocations extracted from a single command segment."""
    cmd_tokens = _strip_leading_env_vars(_tokenize_segment(segment))
    if not cmd_tokens:
        return []
    base = os.path.basename(cmd_tokens[0])
    if base == "git":
        return [cmd_tokens[1:]]
    if base not in SHELL_WRAPPERS:
        return []
    nested = _find_shell_command_arg(cmd_tokens)
    return _iter_git_invocations(nested) if nested is not None else []


def _iter_git_invocations(cmd: str) -> list[list[str]]:
    """Extract tokenized git invocations across command segments and shell -c wrappers."""
    invocations: list[list[str]] = []
    for segment in re.split(r"[;&|\n]+", cmd):
        invocations.extend(_collect_segment_git_invocations(segment))
    return invocations


def _is_push_alias_assignment(cfg_value: str) -> bool:
    """Return True when a -c config entry defines a git alias involving push."""
    lowered = cfg_value.lower()
    return lowered.startswith("alias.") and "push" in lowered


def _consume_git_global_option(git_args: list[str], idx: int) -> tuple[int, bool]:
    """Advance past one global git option at idx and report any push alias config."""
    tok = git_args[idx]
    if tok in GIT_OPTS_TAKING_VAL:
        has_alias = (
            tok == "-c"
            and idx + 1 < len(git_args)
            and _is_push_alias_assignment(git_args[idx + 1])
        )
        return idx + 2, has_alias
    if any(tok.startswith(f"{opt}=") for opt in GIT_OPTS_TAKING_VAL):
        lowered = tok.lower()
        has_alias = (
            lowered.startswith("-c") and "alias." in lowered and "push" in lowered
        )
        return idx + 1, has_alias
    return idx + 1, False


def _git_subcommand_and_args(git_args: list[str]) -> tuple[str, list[str], bool]:
    """Return (subcommand, remaining_args, has_push_alias) after global git flags."""
    has_push_alias = False
    idx = 0
    while idx < len(git_args):
        tok = git_args[idx]
        if tok == "--":
            return "", [], has_push_alias
        if not tok.startswith("-"):
            return tok, git_args[idx + 1 :], has_push_alias
        idx, saw_alias = _consume_git_global_option(git_args, idx)
        has_push_alias = has_push_alias or saw_alias
    return "", [], has_push_alias


def _is_any_git_push(cmd: str) -> bool:
    """Detect any git push (named remote, explicit URL, -C <dir> push, or -c alias=push)."""
    for git_args in _iter_git_invocations(cmd):
        sub, _rest, has_push_alias = _git_subcommand_and_args(git_args)
        if sub == "push" or has_push_alias:
            return True
    return False


def _is_force_flag(tok: str) -> bool:
    """Return True for git push force flags."""
    return tok in ("-f", "--force") or tok.startswith(
        ("--force-with-lease", "--force-if-includes")
    )


def _is_plus_refspec(tok: str) -> bool:
    """Return True for a forced +refspec token."""
    return tok.startswith("+") and len(tok) > 1 and not tok.startswith("+-")


def _targets_protected_branch(tok: str) -> bool:
    """Return True when a refspec targets main, master, or trunk."""
    return bool(PROTECTED_BRANCH_RE.search(tok.lstrip("+")))


def _is_protected_force_push_args(rest: list[str], has_push_alias: bool) -> bool:
    """Return True when push arguments represent a protected force push."""
    if any(_is_plus_refspec(tok) for tok in rest):
        return True
    if not any(_is_force_flag(tok) for tok in rest):
        return False
    return (
        has_push_alias
        or len(rest) <= 2
        or any(_targets_protected_branch(tok) for tok in rest)
    )


def _is_protected_force_push_invocation(git_args: list[str]) -> bool:
    """Return True when a single git invocation is a protected force push."""
    sub, rest, has_push_alias = _git_subcommand_and_args(git_args)
    if sub != "push" and not has_push_alias:
        return False
    return _is_protected_force_push_args(rest, has_push_alias)


def _is_force_push_to_protected(cmd: str) -> bool:
    """Detect force pushes to protected branches and pushes with +refspecs."""
    return any(
        _is_protected_force_push_invocation(git_args)
        for git_args in _iter_git_invocations(cmd)
    )


def _line_mutates_sentinel(line: str) -> bool:
    """Return True when a single shell line modifies or stages .jules/sentinel.md."""
    if not SENTINEL_CMD_RE.search(line):
        return False
    return any(op in line for op in SHELL_SENTINEL_OPS) or bool(
        SENTINEL_GIT_CMD_RE.search(line)
    )


def _mutates_sentinel_in_shell(cmd: str) -> bool:
    """Check whether any shell line/segment writes, edits, copies, or stages .jules/sentinel.md."""
    return any(_line_mutates_sentinel(line) for line in cmd.splitlines())


def _is_sentinel_path(norm: Path) -> bool:
    """Return True when norm ends with .jules/sentinel.md."""
    parts = norm.parts
    return len(parts) >= 2 and parts[-2:] == (".jules", "sentinel.md")


def _is_under_dev_root(norm: Path) -> bool:
    """Return True when norm resolves inside or equal to ~/dev."""
    try:
        real_path = Path(os.path.realpath(str(norm)))
        dev_real = Path(os.path.realpath(str(_dev_root())))
    except OSError:
        return False
    return real_path == dev_real or dev_real in real_path.parents


def _check_file_target(path_str: str, is_proactive: bool) -> tuple[str, str] | None:
    """Return a denial tuple for restricted sentinel or ~/dev file targets, or None."""
    if not path_str:
        return None
    norm = Path(path_str.removeprefix("file://")).expanduser()
    if _is_sentinel_path(norm) and not _has_valid_sentinel_lease(
        str(norm), target_path=norm
    ):
        reason = (
            "Blocked pre-merge write to .jules/sentinel.md in a public repo. "
            "Write Sentinel findings to ~/.gemini/antigravity/proactive-reports/ "
            "and unlock post-merge updates via antigravity-proactive-ctl.sh sentinel-post-merge."
        )
        return ("deny", reason)
    if is_proactive and _is_under_dev_root(norm):
        reason = (
            "Blocked direct edit to primary checkout under ~/dev during "
            "proactive sweep. Edit inside the isolated worktree created by "
            "proactive-worktree.sh instead."
        )
        return ("deny", reason)
    return None


def _read_hook_payload() -> dict[str, Any] | None:
    """Read and decode a JSON object hook payload from stdin."""
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _extract_arg_str(args: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Return the first non-empty string value from args across candidate keys."""
    for key in keys:
        val = args.get(key)
        if val:
            return str(val)
    return ""


def _evaluate_proactive_command(
    cmd: str, allow_draft_pr: bool
) -> tuple[str, str] | None:
    """Return a denial verdict for restricted commands inside proactive sessions."""
    if GH_MERGE_RE.search(cmd):
        return ("deny", "Blocked autonomous PR merge during proactive sweep.")
    if allow_draft_pr:
        return None
    if _is_any_git_push(cmd) or GH_MUTATE_RE.search(cmd):
        reason = (
            "Blocked remote push/PR mutation during local-only (2B) proactive pilot."
        )
        return ("deny", reason)
    return None


def _evaluate_run_command(
    cmd: str, is_proactive: bool, allow_draft_pr: bool
) -> tuple[str, str] | None:
    """Evaluate a run_command payload against universal and proactive guardrails."""
    if _is_force_push_to_protected(cmd):
        return ("deny", "Blocked force-push or +refspec push to protected branch.")
    if _mutates_sentinel_in_shell(cmd) and not _has_valid_sentinel_lease(cmd):
        return ("deny", "Blocked pre-merge modification/staging of .jules/sentinel.md.")
    if GH_PR_CREATE_RE.search(cmd) and SENTINEL_PR_RE.search(cmd):
        reason = (
            "Blocked public PR creation for Sentinel security finding; "
            "use GitHub Security Advisories or keep local-only."
        )
        return ("deny", reason)
    if is_proactive:
        return _evaluate_proactive_command(cmd, allow_draft_pr)
    return None


def _evaluate_tool_call(
    tool_name: str, args: dict[str, Any], is_proactive: bool
) -> tuple[str, str] | None:
    """Evaluate a parsed toolCall entry and return a denial verdict or None."""
    if tool_name in FILE_TOOLS:
        target_path = _extract_arg_str(
            args, ("Path", "path", "TargetFile", "targetFile", "filePath", "file_path")
        )
        return _check_file_target(target_path, is_proactive)
    if tool_name == "run_command":
        cmd = _extract_arg_str(args, ("CommandLine", "command"))
        allow_draft_pr = os.environ.get("AGY_PROACTIVE_ALLOW_DRAFT_PR") == "1"
        return _evaluate_run_command(cmd, is_proactive, allow_draft_pr)
    return None


def main() -> int:
    """Read a PreToolUse hook payload from stdin and emit an allow/deny verdict."""
    payload = _read_hook_payload()
    if payload is None:
        return _emit("allow")

    is_proactive = _is_proactive_session(payload)
    tool_call = payload.get("toolCall")
    if not isinstance(tool_call, dict):
        return _emit("allow")

    tool_name = str(tool_call.get("name") or "")
    raw_args = tool_call.get("args")
    args = raw_args if isinstance(raw_args, dict) else {}
    return _emit_verdict(_evaluate_tool_call(tool_name, args, is_proactive))


if __name__ == "__main__":
    raise SystemExit(main())
