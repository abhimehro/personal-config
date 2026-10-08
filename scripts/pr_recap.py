#!/usr/bin/env python3
"""Agent-Native PR Recap CLI and Synchronization Engine.

Connects Git branch and commit metadata, GitNexus blast-radius analysis,
GitHub pull-request lifecycle events, and Linear workspace state.
Keeps linked Linear issues synchronized with PR lifecycle transitions,
publishes anchored recap comments, and attaches PR diff backlinks.

Designed with Python standard library only (zero external pip dependencies)
for maximum reliability across local macOS, Linux CI, and container runtimes.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import re
import subprocess  # nosec B404
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger("pr_recap")

# ============================================================
# Subprocess Execution Helper
# ============================================================


def _run_cmd(
    cmd: list[str],
    *,
    cwd: str | None = None,
    timeout: float | None = None,
    capture_output: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Execute a local subprocess command with bounded execution."""
    return subprocess.run(  # nosec B603, B607
        cmd,
        cwd=cwd,
        capture_output=capture_output,
        text=text,
        timeout=timeout,
        check=False,
    )


# ============================================================
# Canonical Constants
# ============================================================

DEFAULT_COMMENT_ANCHOR = "<!-- pr-recap-agent-summary -->"
LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"

CANONICAL_STATES = {
    "inProgress": "031c40d8-acc9-4d31-b5f7-ca9efb7206a1",
    "inReview": "7fe5ca3c-51b1-434b-870b-11e6bb92257b",
    "done": "f7acb293-01d7-4339-953f-9a9ddbfb7de1",
    "todo": "04deb3a6-65ae-41ba-b766-e7b9bf091c8b",
}

RELATIONSHIP_PRECEDENCE = {
    "links": 1,
    "contributes": 2,
    "closes": 3,
}

# Regex specifications
BRANCH_ISSUE_RE = re.compile(
    r"^(?:[a-zA-Z0-9_.-]+/)?([A-Za-z]{2,10}-\d{1,7})(?!\.\d)(?:[-/_].*)?$",
    re.IGNORECASE,
)
KEYWORD_ISSUE_RE = re.compile(
    r"\b(Fixes|Closes|Relates\s+to|Contributes\s+to)\s*[:#\s]?\s*([A-Za-z]{2,10}-\d+)(?!\.\d)\b",
    re.IGNORECASE,
)
FALLBACK_ISSUE_RE = re.compile(r"\b([A-Z]{2,10}-\d+)(?!\.\d)\b")
GITHUB_ISSUE_KEYWORD_RE = re.compile(
    r"\b(Fixes|Closes|Resolves|Relates\s+to|Contributes\s+to)\s*[:#\s]?\s*#?(\d+)\b",
    re.IGNORECASE,
)
GITHUB_ISSUE_FALLBACK_RE = re.compile(r"#(\d+)\b")

RelationshipType = Literal["closes", "contributes", "links"]


# ============================================================
# Data Models
# ============================================================


@dataclasses.dataclass(frozen=True)
class Config:
    team_id: str
    state_map: dict[str, str]
    comment_anchor: str = DEFAULT_COMMENT_ANCHOR
    secret_references: dict[str, Any] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Config:
        team_id = data.get("teamId")
        if not team_id or not isinstance(team_id, str) or not team_id.strip():
            raise ValueError(
                "Config validation error: 'teamId' is required and must be a non-empty string."
            )

        state_map_raw = data.get("stateMap") or {}
        if not isinstance(state_map_raw, dict):
            raise ValueError(
                "Config validation error: 'stateMap' must be a dictionary."
            )

        # Merge with canonical defaults for any omitted keys
        merged_state_map = {
            "inProgress": str(
                state_map_raw.get("inProgress") or CANONICAL_STATES["inProgress"]
            ).strip(),
            "inReview": str(
                state_map_raw.get("inReview") or CANONICAL_STATES["inReview"]
            ).strip(),
            "done": str(state_map_raw.get("done") or CANONICAL_STATES["done"]).strip(),
            "todo": str(state_map_raw.get("todo") or CANONICAL_STATES["todo"]).strip(),
        }

        comment_anchor = str(
            data.get("commentAnchor") or DEFAULT_COMMENT_ANCHOR
        ).strip()
        if not comment_anchor:
            comment_anchor = DEFAULT_COMMENT_ANCHOR

        secret_refs_raw = data.get("secretReferences") or {}
        if not isinstance(secret_refs_raw, dict):
            secret_refs_raw = {}

        onepassword_ref = str(
            secret_refs_raw.get("onepassword")
            or "op://Personal/LINEAR_API_KEY/credential"
        ).strip()

        protonpass_raw = secret_refs_raw.get("protonpass")
        if isinstance(protonpass_raw, dict):
            protonpass_ref = {
                "vault": str(protonpass_raw.get("vault") or "Personal").strip(),
                "item": str(protonpass_raw.get("item") or "LINEAR_API_KEY").strip(),
                "field": str(protonpass_raw.get("field") or "Secret").strip(),
            }
        else:
            protonpass_ref = {
                "vault": "Personal",
                "item": "LINEAR_API_KEY",
                "field": "Secret",
            }

        secret_references = {
            "onepassword": onepassword_ref,
            "protonpass": protonpass_ref,
        }

        return cls(
            team_id=team_id.strip(),
            state_map=merged_state_map,
            comment_anchor=comment_anchor,
            secret_references=secret_references,
        )


@dataclasses.dataclass(frozen=True)
class GitNexusAnalysis:
    available: bool
    risk_level: str = "UNKNOWN"
    risk_score: float | None = None
    direct_edits: tuple[str, ...] = ()
    downstream_impact: tuple[str, ...] = ()
    degraded_reason: str | None = None

    def render_markdown(self) -> str:
        if not self.available:
            reason = self.degraded_reason or "GitNexus CLI or index not available"
            return f"- *GitNexus blast-radius analysis degraded: {reason}*"

        lines = [
            f"- **Risk Assessment:** {self.risk_level}"
            + (f" ({self.risk_score:.0f}%)" if self.risk_score is not None else ""),
        ]
        if self.direct_edits:
            lines.append(
                f"- **Direct Structural Edits:** {', '.join(self.direct_edits)}"
            )
        else:
            lines.append(
                "- **Direct Structural Edits:** None detected or index-only changes"
            )

        if self.downstream_impact:
            lines.append(
                f"- **Downstream Impacted Callers/Clusters:** {', '.join(self.downstream_impact)}"
            )
        else:
            lines.append("- **Downstream Impacted Callers/Clusters:** None detected")

        return "\n".join(lines)


@dataclasses.dataclass(frozen=True)
class LinearState:
    id: str
    name: str
    type: str  # backlog, unstarted, started, completed, canceled


@dataclasses.dataclass(frozen=True)
class LinearIssue:
    id: str
    identifier: str
    title: str
    state: LinearState
    comments: tuple[dict[str, Any], ...]
    attachments: tuple[dict[str, Any], ...]


@dataclasses.dataclass(frozen=True)
class PRContext:
    event_name: str
    action: str
    pr_number: int | None
    pr_title: str
    pr_body: str
    pr_url: str
    branch_name: str
    head_sha: str | None
    is_draft: bool
    is_merged: bool
    is_closed: bool
    commit_messages: tuple[str, ...]
    diff_url: str = ""

    def __post_init__(self) -> None:
        if not self.diff_url and self.pr_url:
            object.__setattr__(self, "diff_url", f"{self.pr_url}.diff")


# ============================================================
# Issue Extraction & Precedence
# ============================================================


def normalize_issue_key(raw_key: str) -> str:
    """Normalize issue key to uppercase identifier (e.g. 'proj-123' -> 'PROJ-123')."""
    key = raw_key.strip().upper()
    if key.startswith(("CWE-", "CVE-", "GHSA-")):
        return ""
    return key


def _map_keyword_to_relationship(keyword: str) -> RelationshipType:
    normalized = keyword.strip().lower()
    if normalized in {"fixes", "closes"}:
        return "closes"
    if normalized == "contributes to":
        return "contributes"
    return "links"


def extract_issue_keys(
    branch_name: str = "",
    commit_messages: tuple[str, ...] | list[str] = (),
    pr_title: str = "",
    pr_body: str = "",
    explicit_issues: tuple[str, ...] | list[str] = (),
) -> dict[str, RelationshipType]:
    """Extract issue keys with deterministic precedence across branch, commits, title, and body.

    Mapping:
    - Fixes / Closes -> 'closes'
    - Contributes to -> 'contributes'
    - Plain issue-key reference or Relates to -> 'links'

    Precedence:
    - closes (3) > contributes (2) > links (1)
    """
    found: dict[str, RelationshipType] = {}

    def record(key: str, rel: RelationshipType) -> None:
        norm_key = normalize_issue_key(key)
        if not norm_key:
            return
        if norm_key not in found:
            found[norm_key] = rel
        else:
            current_rank = RELATIONSHIP_PRECEDENCE[found[norm_key]]
            new_rank = RELATIONSHIP_PRECEDENCE[rel]
            if new_rank > current_rank:
                found[norm_key] = rel

    # 0. Explicit issues (CLI overrides)
    for raw in explicit_issues:
        if not raw or not raw.strip():
            continue
        cleaned = raw.strip()
        if ":" in cleaned:
            k, r = cleaned.split(":", 1)
            rel_candidate = r.strip().lower()
            rel = (
                rel_candidate
                if rel_candidate in {"closes", "contributes", "links"}
                else "links"
            )
            record(k, rel)
        else:
            record(cleaned, "links")

    # 1. Branch name matching /(?:feature|fix|chore)\/([A-Z]+-\d+)/i
    if branch_name:
        branch_match = BRANCH_ISSUE_RE.search(branch_name)
        if branch_match:
            record(branch_match.group(1), "links")

    # 2. Commit messages
    for msg in commit_messages:
        if not msg:
            continue
        # Check keyword matches
        for m in KEYWORD_ISSUE_RE.finditer(msg):
            keyword = m.group(1)
            issue_key = m.group(2)
            record(issue_key, _map_keyword_to_relationship(keyword))
        # Check fallback references (uppercase issue identifiers like ABC-105)
        for m in FALLBACK_ISSUE_RE.finditer(msg):
            issue_key = m.group(1)
            record(issue_key, "links")

    # 3. PR Title
    if pr_title:
        for m in KEYWORD_ISSUE_RE.finditer(pr_title):
            keyword = m.group(1)
            issue_key = m.group(2)
            record(issue_key, _map_keyword_to_relationship(keyword))
        for m in FALLBACK_ISSUE_RE.finditer(pr_title):
            record(m.group(1), "links")

    # 4. PR Body
    if pr_body:
        for m in KEYWORD_ISSUE_RE.finditer(pr_body):
            keyword = m.group(1)
            issue_key = m.group(2)
            record(issue_key, _map_keyword_to_relationship(keyword))
        for m in FALLBACK_ISSUE_RE.finditer(pr_body):
            record(m.group(1), "links")

    # Return sorted dictionary for determinism
    return dict(sorted(found.items()))


def extract_github_issue_references(
    commit_messages: tuple[str, ...] | list[str] = (),
    pr_title: str = "",
    pr_body: str = "",
) -> dict[str, RelationshipType]:
    """Extract GitHub issue references like 'Fixes #123' or '#123' for mirrored Linear issue lookup."""
    found: dict[str, RelationshipType] = {}

    def record(num_str: str, rel: RelationshipType) -> None:
        if not num_str or not num_str.isdigit():
            return
        if num_str not in found:
            found[num_str] = rel
        else:
            if RELATIONSHIP_PRECEDENCE[rel] > RELATIONSHIP_PRECEDENCE[found[num_str]]:
                found[num_str] = rel

    for msg in commit_messages:
        if not msg:
            continue
        for m in GITHUB_ISSUE_KEYWORD_RE.finditer(msg):
            record(m.group(2), _map_keyword_to_relationship(m.group(1)))

    if pr_title:
        for m in GITHUB_ISSUE_KEYWORD_RE.finditer(pr_title):
            record(m.group(2), _map_keyword_to_relationship(m.group(1)))
        for m in GITHUB_ISSUE_FALLBACK_RE.finditer(pr_title):
            record(m.group(1), "links")

    if pr_body:
        for m in GITHUB_ISSUE_KEYWORD_RE.finditer(pr_body):
            record(m.group(2), _map_keyword_to_relationship(m.group(1)))
        for m in GITHUB_ISSUE_FALLBACK_RE.finditer(pr_body):
            record(m.group(1), "links")

    return dict(sorted(found.items()))


# ============================================================
# State Transition Engine
# ============================================================


def compute_state_transition(
    current_state: LinearState,
    relationship: RelationshipType,
    context: PRContext,
    state_map: dict[str, str],
) -> tuple[str | None, str]:
    """Calculate target Linear state without regressing advanced issue states.

    Canonical Rules:
    - Branch created or first push -> In Progress only when current issue is Todo or Backlog.
    - Draft PR opened -> In Progress (only when current is Todo or Backlog).
    - PR marked ready for review or review requested -> In Review (advances from Todo, Backlog, or In Progress).
    - PR merged -> Done when the relationship is 'closes'.
    - PR closed without merging -> Todo when closing active work, but never regress completed or already-closed states.

    Returns:
    - (target_state_id, reason) where target_state_id is None if no transition should occur.

    """
    in_progress_id = state_map["inProgress"]
    in_review_id = state_map["inReview"]
    done_id = state_map["done"]
    todo_id = state_map["todo"]

    curr_id = current_state.id
    curr_type = (current_state.type or "").lower()

    # Rule: PR Merged
    if context.is_merged:
        if relationship == "closes":
            if curr_id == done_id or curr_type == "completed":
                return None, f"Issue is already Done ({current_state.name}); no-op"
            return (
                done_id,
                f"PR #{context.pr_number} merged with relationship '{relationship}' -> transition to Done",
            )
        return (
            None,
            f"PR #{context.pr_number} merged, but relationship is '{relationship}' (not 'closes') -> retain current state",
        )

    # Rule: PR Closed without merging
    if context.is_closed and not context.is_merged:
        if curr_type in {"completed", "canceled"}:
            return (
                None,
                f"Issue is already {current_state.name}; preserving manual or terminal state",
            )
        if curr_id in {in_review_id, in_progress_id} or curr_type == "started":
            if curr_id == todo_id:
                return None, "Already in Todo; no-op"
            return (
                todo_id,
                f"PR #{context.pr_number} closed without merge -> transition to Todo",
            )
        return (
            None,
            f"PR #{context.pr_number} closed without merge; current state '{current_state.name}' retained",
        )

    # Rule: Ready for Review (PR ready_for_review, review_requested, or opened non-draft)
    is_ready_for_review = context.action in {
        "ready_for_review",
        "review_requested",
    } or (
        context.event_name == "pull_request"
        and not context.is_draft
        and context.action in {"opened", "reopened"}
    )
    if is_ready_for_review:
        if curr_id == in_review_id:
            return None, "Already in In Review; no-op"
        if curr_type in {"completed", "canceled"}:
            return (
                None,
                f"Issue is already {current_state.name}; refusing to regress terminal state",
            )
        # Advance from backlog, unstarted, or in-progress
        return (
            in_review_id,
            f"PR #{context.pr_number} is ready for review -> transition to In Review",
        )

    # Rule: Draft PR Opened / Synchronized
    if context.is_draft:
        if curr_id == in_progress_id:
            return None, "Already In Progress; no-op"
        if curr_type in {"started", "completed", "canceled"}:
            return (
                None,
                f"Issue is in '{current_state.name}'; non-regression guard prevents moving back to In Progress",
            )
        # Only advance if in backlog or unstarted/todo
        if curr_type in {"backlog", "unstarted"} or curr_id == todo_id:
            return (
                in_progress_id,
                f"Draft PR #{context.pr_number} active -> transition to In Progress",
            )
        return None, f"Retaining state '{current_state.name}' for draft PR"

    # Rule: Branch created or first push / pre-push
    if context.event_name in {"push", "pre-push"}:
        if curr_id == in_progress_id:
            return None, "Already In Progress; no-op"
        if curr_type in {"backlog", "unstarted"} or curr_id == todo_id:
            return (
                in_progress_id,
                f"Branch work detected on '{context.branch_name}' -> transition to In Progress",
            )
        return (
            None,
            f"Issue is already in '{current_state.name}'; non-regression guard prevents setting to In Progress",
        )

    # Default fallback: idempotent no-op
    return None, f"No lifecycle state change triggered for action='{context.action}'"


# ============================================================
# GitNexus Blast-Radius Analyzer
# ============================================================


class GitNexusAnalyzer:
    """Interrogates GitNexus CLI or fallback runner to extract blast radius & risk."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = workspace_root or Path.cwd()

    def analyze(self) -> GitNexusAnalysis:
        runner_cmd = self._find_runner()
        if not runner_cmd:
            return GitNexusAnalysis(
                available=False,
                degraded_reason="GitNexus CLI not found (neither gitnexus, .gitnexus/run.cjs, nor npx available)",
            )

        try:
            cmd = [
                *runner_cmd,
                "detect-changes",
                "--scope",
                "all",
                "--repo",
                str(self.workspace_root),
            ]
            res = _run_cmd(
                cmd,
                cwd=str(self.workspace_root),
                timeout=20,
            )
            if res.returncode != 0:
                err = (res.stderr or res.stdout or "").strip()[:200]
                return GitNexusAnalysis(
                    available=False,
                    degraded_reason=f"GitNexus command failed (exit {res.returncode}): {err}",
                )
            return self._parse_output(res.stdout)
        except subprocess.TimeoutExpired:
            return GitNexusAnalysis(
                available=False,
                degraded_reason="GitNexus command timed out after 20 seconds",
            )
        except Exception as exc:
            return GitNexusAnalysis(
                available=False,
                degraded_reason=f"GitNexus execution error: {exc}",
            )

    def _find_runner(self) -> list[str] | None:
        local_runner = self.workspace_root / ".gitnexus" / "run.cjs"
        if local_runner.is_file():
            return ["node", str(local_runner)]

        # Check for system gitnexus
        gitnexus_path = _run_cmd(["which", "gitnexus"]).stdout.strip()
        if gitnexus_path and os.path.exists(gitnexus_path):
            return [gitnexus_path]

        # Check for npx
        npx_path = _run_cmd(["which", "npx"]).stdout.strip()
        if npx_path:
            return [npx_path, "gitnexus"]

        return None

    def _parse_output(self, output: str) -> GitNexusAnalysis:
        trimmed = output.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            try:
                data = json.loads(trimmed)
                risk = str(data.get("risk") or "UNKNOWN").upper()
                score = float(data["riskScore"]) if "riskScore" in data else None
                direct = tuple(str(x) for x in data.get("changed") or ())
                impact = tuple(str(x) for x in data.get("affected") or ())
                return GitNexusAnalysis(
                    available=True,
                    risk_level=risk,
                    risk_score=score,
                    direct_edits=direct,
                    downstream_impact=impact,
                )
            except Exception as exc:
                logger.debug("GitNexus JSON output parse failed: %s", exc)

        # Text-based parsing for GitNexus CLI
        # Example output:
        # → Changed: 5 symbols in 3 files
        # → Affected: LoginFlow, TokenRefresh, APIMiddlewarePipeline
        # → Risk: MEDIUM
        risk_level = "UNKNOWN"
        risk_score = None
        direct_edits: list[str] = []
        downstream_impact: list[str] = []

        for line in trimmed.splitlines():
            line_str = line.strip().lstrip("→").strip()
            if line_str.lower().startswith("risk:"):
                val = line_str.split(":", 1)[1].strip().upper()
                risk_level = val
            elif line_str.lower().startswith("changed:"):
                val = line_str.split(":", 1)[1].strip()
                if val:
                    direct_edits.extend(
                        [s.strip() for s in val.split(",") if s.strip()]
                    )
            elif line_str.lower().startswith("affected:"):
                val = line_str.split(":", 1)[1].strip()
                if val:
                    downstream_impact.extend(
                        [s.strip() for s in val.split(",") if s.strip()]
                    )

        return GitNexusAnalysis(
            available=True,
            risk_level=risk_level,
            risk_score=risk_score,
            direct_edits=tuple(direct_edits),
            downstream_impact=tuple(downstream_impact),
        )


# ============================================================
# Linear GraphQL Client
# ============================================================


class LinearApiError(RuntimeError):
    pass


class LinearClient:
    """Safe, bounded-retry client for Linear GraphQL API using standard library urllib."""

    def __init__(
        self, api_key: str, max_retries: int = 3, timeout: float = 15.0
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("LinearClient requires a non-empty API key.")
        self._api_key = api_key.strip()
        self.max_retries = max_retries
        self.timeout = timeout

    def _execute_graphql(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        post_data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
            "User-Agent": "pr-recap-sync/1.0",
        }

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if not LINEAR_GRAPHQL_URL.startswith("https://"):
                    raise LinearApiError("Linear API endpoint must use HTTPS")
                req = urllib.request.Request(
                    LINEAR_GRAPHQL_URL,
                    data=post_data,
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(  # noqa: S310  # nosec B310
                    req, timeout=self.timeout
                ) as resp:
                    resp_bytes = resp.read()
                    res_data = json.loads(resp_bytes.decode("utf-8"))

                if "errors" in res_data and res_data["errors"]:
                    err_msgs = [
                        e.get("message", "Unknown GraphQL error")
                        for e in res_data["errors"]
                    ]
                    raise LinearApiError(f"Linear GraphQL error: {'; '.join(err_msgs)}")
                return res_data.get("data") or {}

            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code in {429, 500, 502, 503, 504}:
                    sleep_time = 0.5 * (2 ** (attempt - 1))
                    logger.warning(
                        "Linear API returned HTTP %d on attempt %d/%d; retrying in %.2fs",
                        exc.code,
                        attempt,
                        self.max_retries,
                        sleep_time,
                    )
                    time.sleep(sleep_time)
                    continue
                # 4xx client errors (e.g. 401, 400)
                err_text = ""
                try:
                    err_text = exc.read().decode("utf-8")[:200]
                except Exception as read_exc:
                    logger.debug("Failed to read HTTP error response: %s", read_exc)
                raise LinearApiError(
                    f"Linear HTTP {exc.code} error: {err_text}"
                ) from exc

            except LinearApiError:
                raise

            except Exception as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                sleep_time = 0.5 * (2 ** (attempt - 1))
                time.sleep(sleep_time)

        # Never log API key or secret headers
        raise LinearApiError(
            f"Linear request failed after {self.max_retries} attempts: {last_error}"
        )

    def get_issue(self, issue_key: str) -> LinearIssue | None:
        """Fetch issue details, state, comments, and attachments by identifier or UUID."""
        query = """
        query GetIssue($id: String!) {
          issue(id: $id) {
            id
            identifier
            title
            state {
              id
              name
              type
            }
            comments {
              nodes {
                id
                body
              }
            }
            attachments {
              nodes {
                id
                title
                url
              }
            }
          }
        }
        """
        data = self._execute_graphql(query, {"id": issue_key})
        issue_raw = data.get("issue")
        if not issue_raw:
            return None

        state_raw = issue_raw.get("state") or {}
        state = LinearState(
            id=str(state_raw.get("id") or ""),
            name=str(state_raw.get("name") or ""),
            type=str(state_raw.get("type") or "").lower(),
        )

        comments = tuple(issue_raw.get("comments", {}).get("nodes", []))
        attachments = tuple(issue_raw.get("attachments", {}).get("nodes", []))

        return LinearIssue(
            id=str(issue_raw.get("id")),
            identifier=str(issue_raw.get("identifier")),
            title=str(issue_raw.get("title") or ""),
            state=state,
            comments=comments,
            attachments=attachments,
        )

    def find_issue_by_attachment_url(self, url_fragment: str) -> LinearIssue | None:
        """Find a Linear issue linked to a GitHub issue or PR via Linear Agent attachment."""
        if not url_fragment or not url_fragment.strip():
            return None
        query = """
        query FindIssueByAttachment($url: String!) {
          attachments(filter: { url: { contains: $url } }, first: 1) {
            nodes {
              issue {
                id
                identifier
                title
                state {
                  id
                  name
                  type
                }
                comments {
                  nodes {
                    id
                    body
                  }
                }
                attachments {
                  nodes {
                    id
                    title
                    url
                  }
                }
              }
            }
          }
        }
        """
        try:
            data = self._execute_graphql(query, {"url": url_fragment.strip()})
            nodes = data.get("attachments", {}).get("nodes", [])
            if nodes and nodes[0].get("issue"):
                issue_raw = nodes[0]["issue"]
                state_raw = issue_raw.get("state") or {}
                state = LinearState(
                    id=str(state_raw.get("id") or ""),
                    name=str(state_raw.get("name") or ""),
                    type=str(state_raw.get("type") or "").lower(),
                )
                comments = tuple(issue_raw.get("comments", {}).get("nodes", []))
                attachments = tuple(issue_raw.get("attachments", {}).get("nodes", []))
                return LinearIssue(
                    id=str(issue_raw.get("id")),
                    identifier=str(issue_raw.get("identifier")),
                    title=str(issue_raw.get("title") or ""),
                    state=state,
                    comments=comments,
                    attachments=attachments,
                )
        except Exception as exc:
            logger.debug(
                "Failed querying Linear attachments for '%s': %s", url_fragment, exc
            )
        return None

    def update_issue_state(self, issue_id: str, state_id: str) -> bool:
        """Update issue workflow state."""
        mutation = """
        mutation UpdateIssueState($id: String!, $stateId: String!) {
          issueUpdate(id: $id, input: { stateId: $stateId }) {
            success
          }
        }
        """
        data = self._execute_graphql(mutation, {"id": issue_id, "stateId": state_id})
        return bool(data.get("issueUpdate", {}).get("success", False))

    def upsert_recap_comment(
        self,
        issue: LinearIssue,
        comment_body: str,
        anchor: str = DEFAULT_COMMENT_ANCHOR,
    ) -> tuple[str, bool]:
        """Find existing anchored comment to update, or create a new comment if absent.

        Returns: (comment_id, created_flag)
        """
        existing_comment_id: str | None = None
        for c in issue.comments:
            body = c.get("body") or ""
            if anchor in body:
                existing_comment_id = c.get("id")
                break

        if existing_comment_id:
            # Update existing comment
            mutation = """
            mutation UpdateComment($id: String!, $body: String!) {
              commentUpdate(id: $id, input: { body: $body }) {
                success
                comment {
                  id
                }
              }
            }
            """
            data = self._execute_graphql(
                mutation, {"id": existing_comment_id, "body": comment_body}
            )
            res = data.get("commentUpdate", {})
            return res.get("comment", {}).get("id") or existing_comment_id, False

        # Create new comment
        mutation = """
        mutation CreateComment($issueId: String!, $body: String!) {
          commentCreate(input: { issueId: $issueId, body: $body }) {
            success
            comment {
              id
            }
          }
        }
        """
        data = self._execute_graphql(
            mutation, {"issueId": issue.id, "body": comment_body}
        )
        comment_id = data.get("commentCreate", {}).get("comment", {}).get("id", "")
        return comment_id, True

    def ensure_diff_link(self, issue: LinearIssue, diff_url: str, title: str) -> bool:
        """Ensure the PR diff URL is attached to the issue without duplicates.

        Returns True if created, False if already present.
        """
        if not diff_url:
            return False

        clean_url = diff_url.strip().lower()
        for att in issue.attachments:
            u = str(att.get("url") or "").strip().lower()
            if u == clean_url:
                logger.info(
                    "Diff URL already linked to %s as attachment %s",
                    issue.identifier,
                    att.get("id"),
                )
                return False

        mutation = """
        mutation CreateAttachment($issueId: String!, $title: String!, $url: String!) {
          attachmentCreate(input: { issueId: $issueId, title: $title, url: $url }) {
            success
            attachment {
              id
            }
          }
        }
        """
        data = self._execute_graphql(
            mutation, {"issueId": issue.id, "title": title, "url": diff_url}
        )
        return bool(data.get("attachmentCreate", {}).get("success", False))


# ============================================================
# Recap Comment Formatting
# ============================================================


def build_recap_comment(
    context: PRContext,
    gitnexus: GitNexusAnalysis,
    anchor: str = DEFAULT_COMMENT_ANCHOR,
) -> str:
    """Build the structured Markdown recap comment with anchor tag."""
    state_display = (
        "Merged"
        if context.is_merged
        else (
            "Closed"
            if context.is_closed
            else ("Draft" if context.is_draft else "In Review")
        )
    )
    pr_label = f"#{context.pr_number}" if context.pr_number else "PR"
    title_line = f"{pr_label}: {context.pr_title}" if context.pr_title else pr_label

    summary_text = (
        context.pr_body.strip()
        if context.pr_body and len(context.pr_body.strip()) > 10
        else "Automated synchronization of PR lifecycle and codebase blast radius."
    )

    commits_text = (
        f"{len(context.commit_messages)} commit(s) on `{context.branch_name}`"
        if context.commit_messages
        else f"Branch `{context.branch_name}`"
    )

    diff_section = (
        f"**PR Diff:** [{title_line} Diff]({context.diff_url})"
        if context.diff_url
        else ""
    )

    return (
        f"{anchor}\n"
        f"## 📋 PR Recap: {title_line}\n\n"
        f"- **Status:** {state_display}\n"
        f"- **Branch:** `{context.branch_name}`\n"
        f"- **Commits:** {commits_text}\n"
        f"- **PR URL:** [{title_line}]({context.pr_url})\n"
        f"{diff_section}\n\n"
        f"### 📝 Implementation Summary\n"
        f"{summary_text}\n\n"
        f"### 🔍 GitNexus Blast-Radius Analysis\n"
        f"{gitnexus.render_markdown()}\n\n"
        f"### ✅ Verification & Lifecycle State\n"
        f"- Lifecycle Event: `{context.event_name}` (`{context.action}`)\n"
        f"- Draft Mode: `{context.is_draft}` | Merged: `{context.is_merged}` | Closed: `{context.is_closed}`\n"
        f"- Automated Sync: Successfully reconciled with Linear workspace.\n"
    )


# ============================================================
# Context Resolution (GitHub Actions & Local)
# ============================================================


def resolve_pr_context(args: argparse.Namespace) -> PRContext:
    """Resolve PR context from GitHub Actions environment, event JSON, or local git state."""
    event_path = args.event_path or os.getenv("GITHUB_EVENT_PATH")
    event_name = (
        args.event_name
        or os.getenv("GITHUB_EVENT_NAME")
        or ("pre-push" if args.pre_push else "local")
    )

    event_payload: dict[str, Any] = {}
    if event_path and os.path.isfile(event_path):
        try:
            with open(event_path, "r", encoding="utf-8") as f:
                event_payload = json.load(f)
        except Exception as exc:
            logger.warning("Failed to load GITHUB_EVENT_PATH '%s': %s", event_path, exc)

    pr_payload = event_payload.get("pull_request") or {}

    # Extract action
    action = (
        args.action
        or event_payload.get("action")
        or ("opened" if args.pre_push else "sync")
    )

    # PR Number
    pr_number = args.pr_number
    if pr_number is None and pr_payload.get("number"):
        try:
            pr_number = int(pr_payload["number"])
        except (ValueError, TypeError):
            pass

    # PR Title & Body
    pr_title = args.pr_title or pr_payload.get("title") or ""
    pr_body = args.pr_body or pr_payload.get("body") or ""

    # PR URL
    pr_url = args.pr_url or pr_payload.get("html_url") or ""

    # Branch Name
    branch_name = args.branch
    if not branch_name:
        branch_name = pr_payload.get("head", {}).get("ref") or ""
    if not branch_name:
        try:
            res = _run_cmd(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                timeout=5,
            )
            if res.returncode == 0:
                branch_name = res.stdout.strip()
        except Exception as exc:
            logger.debug("Failed to detect branch name: %s", exc)
            branch_name = "unknown"

    # Head SHA
    head_sha = pr_payload.get("head", {}).get("sha")
    if not head_sha:
        try:
            res = _run_cmd(
                ["git", "rev-parse", "HEAD"],
                timeout=5,
            )
            if res.returncode == 0:
                head_sha = res.stdout.strip()
        except Exception as exc:
            logger.debug("Failed to detect head sha: %s", exc)

    # Flags
    is_draft = (
        args.is_draft
        if args.is_draft is not None
        else bool(pr_payload.get("draft", False))
    )
    is_merged = (
        args.is_merged
        if args.is_merged is not None
        else bool(pr_payload.get("merged", False))
    )
    is_closed = (
        args.is_closed
        if args.is_closed is not None
        else (pr_payload.get("state") == "closed" or action == "closed")
    )

    # Auto-detect PR details locally via gh CLI if not provided and on a feature branch
    if (
        not pr_payload
        and not pr_url
        and not pr_number
        and branch_name
        and branch_name not in {"main", "master", "develop", "unknown"}
    ):
        try:
            gh_res = _run_cmd(
                ["gh", "pr", "view", "--json", "number,title,body,url,isDraft,state"],
                timeout=5,
            )
            if gh_res.returncode == 0 and gh_res.stdout.strip():
                pr_data = json.loads(gh_res.stdout)
                if not pr_number and pr_data.get("number"):
                    pr_number = int(pr_data["number"])
                if not pr_title and pr_data.get("title"):
                    pr_title = pr_data["title"]
                if not pr_body and pr_data.get("body"):
                    pr_body = pr_data["body"]
                if not pr_url and pr_data.get("url"):
                    pr_url = pr_data["url"]
                if is_draft is None and "isDraft" in pr_data:
                    is_draft = bool(pr_data["isDraft"])
                if is_closed is None and pr_data.get("state") == "CLOSED":
                    is_closed = True
                if is_merged is None and pr_data.get("state") == "MERGED":
                    is_merged = True
        except Exception as exc:
            logger.debug("Failed to query gh pr view: %s", exc)

    # Commits
    commit_messages: list[str] = []
    if args.commit_message:
        commit_messages.append(args.commit_message)
    else:
        # Check commits in event_payload
        commits_raw = event_payload.get("commits") or ()
        for c in commits_raw:
            if isinstance(c, dict) and c.get("message"):
                commit_messages.append(c["message"])

        # Try local git commits if none in event
        if not commit_messages:
            try:
                res = _run_cmd(
                    ["git", "log", "-n", "10", "--format=%s%n%b"],
                    timeout=5,
                )
                if res.returncode == 0 and res.stdout.strip():
                    commit_messages.extend(
                        [m.strip() for m in res.stdout.split("\n\n") if m.strip()]
                    )
            except Exception as exc:
                logger.debug("Failed to read git log: %s", exc)

    return PRContext(
        event_name=event_name,
        action=action,
        pr_number=pr_number,
        pr_title=pr_title,
        pr_body=pr_body,
        pr_url=pr_url,
        branch_name=branch_name,
        head_sha=head_sha,
        is_draft=is_draft,
        is_merged=is_merged,
        is_closed=is_closed,
        commit_messages=tuple(commit_messages),
    )


# ============================================================
# Config Loader & Validation
# ============================================================


def load_config(config_path: Path | None = None) -> Config:
    """Load and validate configuration from .pr-recap.json."""
    candidate_paths: list[Path] = []
    if config_path:
        candidate_paths.append(config_path)
    else:
        candidate_paths.append(Path(".pr-recap.json"))
        try:
            repo_root = _run_cmd(
                ["git", "rev-parse", "--show-toplevel"],
                timeout=5,
            ).stdout.strip()
            if repo_root:
                candidate_paths.append(Path(repo_root) / ".pr-recap.json")
        except Exception as exc:
            logger.debug("Failed to determine git toplevel: %s", exc)

    found_path: Path | None = None
    for p in candidate_paths:
        if p.is_file():
            found_path = p
            break

    if not found_path:
        team_id = os.getenv("LINEAR_TEAM_ID", "personal-config")
        logger.info(
            "No .pr-recap.json file found; falling back to default configuration with teamId='%s'",
            team_id,
        )
        return Config(
            team_id=team_id,
            state_map=dict(CANONICAL_STATES),
            comment_anchor=DEFAULT_COMMENT_ANCHOR,
            secret_references={
                "onepassword": "op://Personal/LINEAR_API_KEY/credential",
                "protonpass": {
                    "vault": "Personal",
                    "item": "LINEAR_API_KEY",
                    "field": "Secret",
                },
            },
        )

    try:
        with open(found_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse config file '{found_path}': invalid JSON ({exc})"
        ) from exc

    return Config.from_dict(data)


# ============================================================
# Provider-Agnostic Secret Resolution (1Password, Proton Pass)
# ============================================================


def _find_onepassword_binary() -> str | None:
    """Locate 1Password CLI binary ('op')."""
    candidates = ["op", "/opt/homebrew/bin/op", "/usr/local/bin/op"]
    for c in candidates:
        try:
            if "/" in c:
                if os.path.isfile(c) and os.access(c, os.X_OK):
                    return c
            else:
                res = _run_cmd(["which", c])
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
        except Exception as exc:
            logger.debug("Failed checking 1Password candidate %s: %s", c, exc)
    return None


def _find_protonpass_binary() -> str | None:
    """Locate Proton Pass CLI binary ('pass-cli')."""
    home = os.path.expanduser("~")
    candidates = [
        "pass-cli",
        os.path.join(home, ".local", "bin", "pass-cli"),
        "/usr/local/bin/pass-cli",
        "/opt/homebrew/bin/pass-cli",
    ]
    for c in candidates:
        try:
            if "/" in c:
                if os.path.isfile(c) and os.access(c, os.X_OK):
                    return c
            else:
                res = _run_cmd(["which", c])
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
        except Exception as exc:
            logger.debug("Failed checking Proton Pass candidate %s: %s", c, exc)
    return None


def resolve_linear_api_key(
    config: Config | None = None,
    timeout: float = 8.0,
) -> tuple[str | None, str]:
    """Resolve Linear API key across environment, 1Password, and Proton Pass.

    Resolution Order:
    1. LINEAR_API_KEY (or LINEAR_TOKEN) environment variable
    2. 1Password CLI ('op read --force') using secret reference
    3. Proton Pass CLI ('pass-cli item view') using vault/item/field
    4. None (actionable failure)

    Security Invariant:
    Never logs, prints, or echoes the secret key value or fragments.

    Returns:
    - (api_key, provider_source) e.g. ("lin_api_...", "1password") or (None, "none")

    """
    # 1. Environment variable (preserves CI, containers, and explicit runs)
    env_key = os.getenv("LINEAR_API_KEY") or os.getenv("LINEAR_TOKEN")
    if env_key and env_key.strip():
        logger.debug("Resolved Linear API key from environment variable")
        return env_key.strip(), "environment"

    # Default secret references
    sec_refs = config.secret_references if config else {}
    op_ref = sec_refs.get("onepassword") or "op://Personal/LINEAR_API_KEY/credential"
    proton_ref = sec_refs.get("protonpass") or {
        "vault": "Personal",
        "item": "LINEAR_API_KEY",
        "field": "Secret",
    }

    # 2. 1Password CLI (op)
    op_bin = _find_onepassword_binary()
    if op_bin:
        try:
            cmd = [op_bin, "read", "--force", str(op_ref)]
            res = _run_cmd(
                cmd,
                timeout=timeout,
            )
            if res.returncode == 0:
                val = res.stdout.strip()
                if val:
                    logger.debug(
                        "Resolved Linear API key via 1Password secret reference"
                    )
                    return val, "1password"
            else:
                logger.debug("1Password CLI read returned exit %d", res.returncode)
        except subprocess.TimeoutExpired:
            logger.debug("1Password CLI read timed out after %.1fs", timeout)
        except Exception as exc:
            logger.debug("1Password CLI read error: %s", exc)

    # 3. Proton Pass CLI (pass-cli)
    pass_bin = _find_protonpass_binary()
    if pass_bin:
        try:
            vault_name = "Personal"
            item_title = "LINEAR_API_KEY"
            field_name = "Secret"
            if isinstance(proton_ref, dict):
                vault_name = proton_ref.get("vault") or vault_name
                item_title = proton_ref.get("item") or item_title
                field_name = proton_ref.get("field") or field_name

            cmd = [
                pass_bin,
                "item",
                "view",
                "--vault-name",
                vault_name,
                "--item-title",
                item_title,
                "--field",
                field_name,
            ]
            res = _run_cmd(
                cmd,
                timeout=timeout,
            )
            if res.returncode == 0 and res.stdout.strip():
                # Filter out update notices or empty lines
                lines = [
                    ln.strip()
                    for ln in res.stdout.splitlines()
                    if ln.strip()
                    and not ln.strip().lower().startswith("new update available")
                ]
                if lines:
                    val = lines[-1]
                    if val:
                        logger.debug("Resolved Linear API key via Proton Pass CLI")
                        return val, "protonpass"
            else:
                logger.debug("Proton Pass CLI read returned exit %d", res.returncode)
        except subprocess.TimeoutExpired:
            logger.debug("Proton Pass CLI read timed out after %.1fs", timeout)
        except Exception as exc:
            logger.debug("Proton Pass CLI read error: %s", exc)

    logger.debug("Could not resolve Linear API key from any provider")
    return None, "none"


# ============================================================
# Main Orchestration: pr-recap sync
# ============================================================


def _handle_missing_linear_key(config: Config, dry_run: bool) -> int:
    """Log actionable error or warning when Linear API key cannot be resolved."""
    op_ref = config.secret_references.get(
        "onepassword", "op://Personal/LINEAR_API_KEY/credential"
    )
    proton_ref = config.secret_references.get("protonpass", {})
    proton_vault = (
        proton_ref.get("vault", "Personal")
        if isinstance(proton_ref, dict)
        else "Personal"
    )
    proton_item = (
        proton_ref.get("item", "LINEAR_API_KEY")
        if isinstance(proton_ref, dict)
        else "LINEAR_API_KEY"
    )
    proton_field = (
        proton_ref.get("field", "Secret")
        if isinstance(proton_ref, dict)
        else "Secret"
    )

    if dry_run:
        logger.warning(
            "No Linear API key resolved from environment, 1Password (%s), or Proton Pass. "
            "Dry-run mode will plan without network mutations.",
            op_ref,
        )
        return 0

    logger.error(
        "Linear API key could not be resolved from any available provider:\n"
        "  1. Environment variable: LINEAR_API_KEY (or LINEAR_TOKEN)\n"
        "  2. 1Password CLI: %s\n"
        "  3. Proton Pass CLI: vault='%s', item='%s', field='%s'\n\n"
        "Action items:\n"
        "  - 1Password: Ensure desktop app integration is enabled, or set OP_SERVICE_ACCOUNT_TOKEN, or run:\n"
        "      op run --env-file=.env.pr-recap.template -- pr-recap sync\n"
        "  - Proton Pass: Ensure active session ('pass-cli login'), or run:\n"
        "      pass-cli run --env-file=.env.pr-recap.template -- pr-recap sync\n"
        "  - Shell/CI: Export LINEAR_API_KEY\n"
        "  - Dry-run: Run with --dry-run to preview actions without mutations.",
        op_ref,
        proton_vault,
        proton_item,
        proton_field,
    )
    return 1


def _sync_single_issue(
    issue_key: str,
    relationship: RelationshipType,
    context: PRContext,
    config: Config,
    comment_body: str,
    linear_client: LinearClient | None,
    dry_run: bool,
) -> bool:
    """Reconcile state, upsert comment, and attach diff link for a single Linear issue."""
    logger.info("--- Processing issue %s (relationship=%s) ---", issue_key, relationship)
    if not linear_client:
        logger.info("[DRY RUN] Would fetch and reconcile issue %s", issue_key)
        return True

    try:
        issue = linear_client.get_issue(issue_key)
    except LinearApiError as exc:
        if dry_run and "entity not found" in str(exc).lower():
            logger.info(
                "[DRY RUN] Issue %s not found in Linear workspace; simulating plan.",
                issue_key,
            )
            issue = None
        else:
            raise

    if not issue:
        if dry_run:
            logger.info("[DRY RUN] Would plan reconciliation for issue %s", issue_key)
            return True
        logger.error("Linear issue '%s' not found in workspace.", issue_key)
        return False

    logger.info(
        "Found issue %s: '%s' currently in state '%s' (%s)",
        issue.identifier,
        issue.title,
        issue.state.name,
        issue.state.id,
    )

    # Compute State Transition
    target_state_id, reason = compute_state_transition(
        current_state=issue.state,
        relationship=relationship,
        context=context,
        state_map=config.state_map,
    )
    logger.info("State transition evaluation: %s", reason)

    had_error = False
    if target_state_id and not dry_run:
        updated = linear_client.update_issue_state(issue.id, target_state_id)
        if updated:
            logger.info(
                "Successfully updated state for %s to %s",
                issue.identifier,
                target_state_id,
            )
        else:
            logger.error("Failed to update state for %s", issue.identifier)
            had_error = True
    elif target_state_id and dry_run:
        logger.info(
            "[DRY RUN] Would update state for %s to %s",
            issue.identifier,
            target_state_id,
        )

    # Upsert Recap Comment
    if not dry_run:
        comment_id, created = linear_client.upsert_recap_comment(
            issue=issue,
            comment_body=comment_body,
            anchor=config.comment_anchor,
        )
        action_str = "Created" if created else "Updated"
        logger.info(
            "%s anchored recap comment (%s) on issue %s",
            action_str,
            comment_id,
            issue.identifier,
        )
    else:
        logger.info(
            "[DRY RUN] Would upsert anchored recap comment on issue %s",
            issue.identifier,
        )

    # Attach PR Diff Link
    if context.diff_url:
        title = (
            f"PR #{context.pr_number} Diff"
            if context.pr_number
            else f"{context.pr_title} Diff"
        )
        if not dry_run:
            created_link = linear_client.ensure_diff_link(
                issue=issue,
                diff_url=context.diff_url,
                title=title,
            )
            if created_link:
                logger.info(
                    "Added PR diff link '%s' to %s",
                    context.diff_url,
                    issue.identifier,
                )
            else:
                logger.info("PR diff link already present on %s", issue.identifier)
        else:
            logger.info(
                "[DRY RUN] Would attach diff link '%s' to %s",
                context.diff_url,
                issue.identifier,
            )

    return not had_error


def run_sync(args: argparse.Namespace) -> int:
    """Run synchronization between Git/GitHub, GitNexus, and Linear."""
    # 1. Load config
    try:
        config = load_config(Path(args.config) if args.config else None)
    except Exception as exc:
        logger.error("Configuration error: %s", exc)
        return 1

    # 2. Resolve PR Context
    context = resolve_pr_context(args)

    # 3. Extract Issue Keys & Relationships
    issue_map = extract_issue_keys(
        branch_name=context.branch_name,
        commit_messages=context.commit_messages,
        pr_title=context.pr_title,
        pr_body=context.pr_body,
        explicit_issues=getattr(args, "issue", None) or (),
    )

    # 4. Resolve Linear API Key across providers (env -> 1Password -> Proton Pass)
    key_timeout = float(os.getenv("PR_RECAP_KEY_TIMEOUT", "8.0"))
    linear_key, key_source = resolve_linear_api_key(config=config, timeout=key_timeout)

    if linear_key:
        logger.info("Resolved Linear API key via %s", key_source)
        linear_client = LinearClient(api_key=linear_key)
    else:
        linear_client = None

    # 4b. Mirrored Linear Agent resolution fallback (when branch/commits link via GitHub issues or PR URLs)
    if not issue_map and linear_client:
        if context.pr_number:
            pr_match = linear_client.find_issue_by_attachment_url(
                f"pull/{context.pr_number}"
            )
            if pr_match:
                logger.info(
                    "Resolved Linear issue %s from GitHub PR #%d attachment in Linear",
                    pr_match.identifier,
                    context.pr_number,
                )
                issue_map[pr_match.identifier] = "links"

        gh_issues = extract_github_issue_references(
            commit_messages=context.commit_messages,
            pr_title=context.pr_title,
            pr_body=context.pr_body,
        )
        for gh_num, gh_rel in gh_issues.items():
            mirrored = linear_client.find_issue_by_attachment_url(f"issues/{gh_num}")
            if mirrored:
                logger.info(
                    "Resolved mirrored Linear issue %s from GitHub issue #%s (relationship=%s) via Linear Agent attachment",
                    mirrored.identifier,
                    gh_num,
                    gh_rel,
                )
                issue_map[mirrored.identifier] = gh_rel

    if not issue_map:
        logger.info(
            "No Linear issue keys or mirrored GitHub issues found across branch '%s', title, body, or commits. Exiting cleanly (safe no-op).",
            context.branch_name,
        )
        return 0

    if not linear_client:
        err_code = _handle_missing_linear_key(config, args.dry_run)
        if err_code != 0 or not args.dry_run:
            return err_code

    logger.info("Extracted %d linked issue(s): %s", len(issue_map), issue_map)

    # 5. Run GitNexus Analysis
    analyzer = GitNexusAnalyzer()
    gitnexus_result = analyzer.analyze()
    if gitnexus_result.available:
        logger.info("GitNexus analysis completed: Risk=%s", gitnexus_result.risk_level)
    else:
        logger.info("GitNexus degraded: %s", gitnexus_result.degraded_reason)

    # 6. Format Recap Comment
    comment_body = build_recap_comment(
        context=context,
        gitnexus=gitnexus_result,
        anchor=config.comment_anchor,
    )

    # 7. Synchronize each issue
    had_error = False
    for issue_key, relationship in issue_map.items():
        try:
            ok = _sync_single_issue(
                issue_key=issue_key,
                relationship=relationship,
                context=context,
                config=config,
                comment_body=comment_body,
                linear_client=linear_client,
                dry_run=args.dry_run,
            )
            if not ok:
                had_error = True
        except Exception as exc:
            logger.error("Error processing issue %s: %s", issue_key, exc)
            had_error = True

    return 1 if had_error else 0


# ============================================================
# CLI Setup
# ============================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pr-recap",
        description="Agent-Native PR Recap CLI: Synchronize PR lifecycle with Linear & GitNexus.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 'sync' subcommand
    sync_parser = subparsers.add_parser(
        "sync", help="Synchronize PR metadata, GitNexus, and Linear state."
    )
    sync_parser.add_argument(
        "--config", help="Path to .pr-recap.json configuration file."
    )
    sync_parser.add_argument(
        "--event-path", help="Path to GitHub Actions event payload JSON."
    )
    sync_parser.add_argument(
        "--event-name", help="GitHub event name (e.g. pull_request, push)."
    )
    sync_parser.add_argument(
        "--action", help="Lifecycle action (opened, ready_for_review, closed, etc.)."
    )
    sync_parser.add_argument("--pr-number", type=int, help="Pull request number.")
    sync_parser.add_argument("--pr-title", help="Pull request title.")
    sync_parser.add_argument("--pr-body", help="Pull request body.")
    sync_parser.add_argument("--pr-url", help="Pull request HTML URL.")
    sync_parser.add_argument("--branch", help="Git branch name.")
    sync_parser.add_argument(
        "--commit-message", help="Commit message to extract keys from."
    )
    sync_parser.add_argument(
        "--issue",
        action="append",
        help="Target Linear issue identifier (e.g. ABHI-123 or ABHI-123:closes). Can be specified multiple times.",
    )
    sync_parser.add_argument(
        "--is-draft",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="PR draft state.",
    )
    sync_parser.add_argument(
        "--is-merged",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="PR merged state.",
    )
    sync_parser.add_argument(
        "--is-closed",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="PR closed state.",
    )
    sync_parser.add_argument(
        "--pre-push", action="store_true", help="Run in local pre-push validation mode."
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate and log actions without mutating Linear.",
    )
    sync_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose debug logging."
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    log_level = logging.DEBUG if getattr(args, "verbose", False) else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s [%(levelname)s] %(message)s"
    )

    if args.subcommand == "sync":
        code = run_sync(args)
        sys.exit(code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
