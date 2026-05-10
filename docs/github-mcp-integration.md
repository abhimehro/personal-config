# GitHub MCP Integration for Repository Automation

> **Status: not implemented.** The previous MCP compatibility layer
> (`MCP_AVAILABLE`, `USE_MCP_GITHUB`, `mcp_json`, `mcp_text`, and the MCP
> branches inside `latest_tag_for_action` / `tag_exists`) has been removed
> because no real MCP backend was wired up — the placeholder branches either
> delegated to the `gh` CLI anyway or, in the case of `tag_exists`,
> unconditionally returned `True` without verifying the tag.
>
> The repository automation scripts now always use the `gh` CLI directly via
> the helpers in `.github/scripts/repository_automation_common.py`. The
> `USE_MCP_GITHUB` environment variable is no longer read and has no effect.
>
> If MCP-backed automation is reintroduced in the future, the new
> implementation must:
>
> - actually call an MCP client (not just delegate to `gh_json` / `gh_text`),
> - verify tag existence rather than returning a placeholder value, and
> - keep the `gh` CLI as a working fallback path.
