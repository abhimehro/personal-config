# CLI capability matrix

Installed (2026-08-27, Apple Silicon):

| Binary         | Path                        | Version            |
| -------------- | --------------------------- | ------------------ |
| `agy`          | `~/.local/bin/agy`          | 1.1.22             |
| `cursor`       | `~/.local/bin/cursor`       | 3.17.21            |
| `cursor-agent` | `~/.local/bin/cursor-agent` | 2026.06.29-71f0784 |
| `vibe`         | `~/.local/bin/vibe`         | 2.16.1             |
| `gh`           | `/opt/homebrew/bin/gh`      | 2.98.0             |
| `devin`        | `/opt/homebrew/bin/devin`   | 3000.6.2           |

Official Cursor command is `agent`. This machine provides `cursor-agent`.

## Native surfaces

| Surface            | Antigravity                                                   | Cursor CLI                               | Vibe                                         | Devin                                           | gh                                   |
| ------------------ | ------------------------------------------------------------- | ---------------------------------------- | -------------------------------------------- | ----------------------------------------------- | ------------------------------------ |
| MCP                | `~/.gemini/config/mcp_config.json`, `.agents/mcp_config.json` | `~/.cursor/mcp.json`, `.cursor/mcp.json` | `[[mcp_servers]]` in `config.toml`           | `mcp_config.json` (v3000.3+)                    | no                                   |
| OAuth MCP          | yes                                                           | yes                                      | **no**                                       | yes                                             | n/a                                  |
| Hooks              | plugin `hooks.json`                                           | `.cursor/hooks.json`                     | `hooks.toml`                                 | `.devin/hooks.v1.json`                          | no (use git hooks / `gh` extensions) |
| Agents / subagents | `/agents`, plugin `agents/`                                   | Cursor subagents                         | `~/.vibe/agents/*.toml`                      | skills + plugins                                | `gh agent-task`                      |
| Skills             | `~/.gemini/antigravity-cli/skills`, `.agents/skills`          | `.cursor/skills`, `.agents/skills`       | `.agents/skills`, `~/.vibe/skills`           | `.agents/skills`, `.devin/skills`               | `gh skill` (docs/version specific)   |
| Rules              | plugin `rules/`, `AGENTS.md`                                  | `.cursor/rules`, `AGENTS.md`             | project context / `AGENTS.md`                | `.devin/rules`, imports, `AGENTS.md`            | none                                 |
| Permissions        | `toolPermission`, `mcp(server/tool)`                          | `cli-config.json` allow/deny             | `[tools.*]`, agents                          | `auto` / `accept-edits` / `smart` / `dangerous` | auth scopes                          |
| Sandbox            | `sandbox-exec` (`enableTerminalSandbox`)                      | CLI sandbox (currently live-disabled)    | no macOS seatbelt equivalent documented here | `--sandbox`                                     | n/a                                  |
| Models             | `/model`, Gemini family                                       | `cli-config.json` `model`                | `active_model`, providers in TOML            | `--model`, adaptive                             | `gh models` extension                |

## Live gaps (do not copy forward)

| Tool                          | Gap                                                                                     | Hub default                                                                  |
| ----------------------------- | --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Cursor repo `cli-config.json` | `approvalMode: unrestricted`, no deny rules, sandbox disabled                           | portable `ai/adapters/cursor/cli.json`: allowlist + deny secrets/destructive |
| Cursor home hooks             | `./hooks/allow-shell.sh` is wrong as a project path                                     | keep project hooks as `.cursor/hooks/...`                                    |
| Vibe                          | `bypass_tool_permissions = true`, `auto-approve` available, JSON MCP file is unofficial | `bypass_tool_permissions = false`, TOML MCP adapter                          |
| Devin                         | `skip_workspace_trust: true`, empty sandbox, legacy `.devin/hooks.json`                 | keep trust on, add `hooks.v1.json` only after review                         |
| Antigravity                   | live `toolPermission: always-proceed`, `allowNonWorkspaceAccess: true`                  | request-review + workspace-only adapter                                      |
| gh                            | no MCP/hooks framework                                                                  | aliases + extensions + existing auth scripts                                 |
| MCP template                  | many paid search duplicates, Filesystem `~/dev/`, AppleScript on by default             | profile filter, Filesystem off in `core-safe`                                |

## gh scope

`gh` is not an agent runtime. Hub coverage:

- Secret-free `ai/adapters/gh/config.yml` (`git_protocol=ssh`, telemetry off)
- Existing `scripts/ensure_gh_token.sh`, `scripts/verify_gh_auth.sh`,
  `scripts/install_gh_extensions.sh`
- Skills: `.agents/skills/gh-stack/`
- Never inspect or commit `~/.config/gh/hosts.yml`
