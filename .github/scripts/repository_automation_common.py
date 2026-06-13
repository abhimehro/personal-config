from typing import Any
def release_url(tag_name: str) -> str:
    slug = repository_slug()
    if not slug or not tag_name:
        return ""
    return f"https://github.com/{slug}/releases/tag/{tag_name}"


def latest_tag_for_action(repo_id: str) -> str:
    latest = gh_text(["api", f"repos/{repo_id}/releases/latest", "--jq", ".tag_name"])
    if latest:
        return latest
    return gh_text(["api", f"repos/{repo_id}/tags?per_page=1", "--jq", ".[0].name"])


def is_commit_sha(ref: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", ref))


def numeric_version(text: str) -> tuple[int, int, int] | None:
    if is_commit_sha(text):
        return None
    match = re.search(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", text)
    if not match:
        return None
    return tuple(int(group or 0) for group in match.groups())


def target_ref(current: str, latest: str) -> str | None:
    if is_commit_sha(current):
        return None
    current_v = numeric_version(current)
    latest_v = numeric_version(latest)
    if not current_v or not latest_v:
        return None
    if latest_v <= current_v:
        return None
    if re.fullmatch(r"v?\d+", current):
        prefix = "v" if current.startswith("v") or latest.startswith("v") else ""
        return f"{prefix}{latest_v[0]}"
    return latest


def append_publication_result(
    body: str,
    *,
    title: str,
    labels: list[Any],
    noun: str,
) -> tuple[str, str, str | None]:
    if not writes_allowed():
        body += f"\n## Write gate\n- {noun} publication skipped because this run is in report-only mode.\n"
        return body, "", None
    if not ensure_gh_token():
        body += f"\n## Publishing failure\n- GH_TOKEN is missing, so the {noun} could not be created.\n"
        return body, "", "missing GH_TOKEN"
    try:
        issue_url = create_or_update_issue(title, body, labels)
        body += f"\n## Published issue\n- {issue_url}\n"
        return body, issue_url, None
    except Exception as exc:  # pragma: no cover - runtime integration
        body += f"\n## Publishing failure\n- {type(exc).__name__}\n"
        return body, "", type(exc).__name__
