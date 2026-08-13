# Agent shell configuration matrix

Last updated: 2026-08-13

This doc explains **what is shared**, **what is separate**, and **where to
configure** each agent host so local Fish never breaks POSIX agent commands.

## Mental model

| Layer                                                                    | What it controls                                    | Shared across tools?                            | Fish risk                                            |
| :----------------------------------------------------------------------- | :-------------------------------------------------- | :---------------------------------------------- | :--------------------------------------------------- |
| macOS login shell                                                        | Interactive human terminal (Fish)                   | OS-wide                                         | N/A (intentional)                                    |
| `agent-zsh` / `agent-bash`                                               | Clean POSIX env for agents                          | **Shared primitive** used by all local tools    | None if used                                         |
| IDE terminal profile (Cursor/VS Code/Windsurf)                           | Integrated terminal + often agent/automation shells | Per IDE user settings (not synced to cloud VMs) | High if default is Fish                              |
| Local CLI agents (Vibe, Claude Code, Codex, Cursor CLI, Antigravity CLI) | How the agent spawns shell tools on this Mac        | Per-product config + repo `AGENTS.md` / rules   | High unless prefixed or IDE/default shell overridden |
| Cloud agents (Devin, cloud sandboxes)                                    | Remote Linux VM shell                               | **Separate** (blueprint / VM image)             | Low (no Fish)                                        |
| Raycast Script Commands / AI Terminal                                    | Explicit shebang or Terminal extension command      | Per script / per invocation                     | Low if shebang is bash/zsh                           |

**Key rule:** nothing auto-inherits `agent-zsh` unless the **host tool** is
configured to launch it, or the agent is instructed to prefix commands.

## Shared local primitive (configure once)

In-repo sources:

- Launchers: `configs/bin/agent-{zsh,bash,session,term-doctor,shell-selftest}`
- Profiles: `configs/.config/agent-shell/` (`zshrc`, `zshenv`, `bashrc`)
- Overview: `configs/.config/agent-shell/README.md`

Typical install on the Mac: symlink or copy launchers onto `PATH` (for example
`~/bin`), then:

```bash
agent-zsh -c 'git status -sb'
agent-bash -c 'git status -sb'
agent-term-doctor
```

Doctor logs (local only; do not commit):

```text
~/.local/state/agent-term-doctor/session-<utc>-<pid>.log
~/.local/state/agent-term-doctor/latest.log
```

## Per-host configuration

### 1. Cursor IDE (local)

- **User settings:** `~/Library/Application Support/Cursor/User/settings.json`
- **Workspace settings:** `.vscode/settings.json`
- Set `terminal.integrated.defaultProfile.osx` / automation profile to
  `agent-zsh` when you want the IDE agent terminal on the POSIX launcher
- **Does not sync** to Devin/cloud VMs
- Cursor CLI (`agent`) is separate from IDE terminal profiles — still needs
  `agent-zsh -c` / explicit instructions

### 2. Cursor CLI

- Config: `~/.cursor/cli-config.json` (permissions, attribution, sandbox)
- Shell behavior: follows process environment + instructions in repo
- Action: document prefix in `AGENTS.md` / `.cursor/rules/agent-shell.mdc`

### 3. Mistral Vibe

- Config: `~/.vibe/config.toml`, `~/.vibe/AGENTS.md`
- Runs tools **locally**; bash tool often starts under login shell context
- Action: prefer commands via `agent-zsh -c`; keep interactive shells denylisted
- Vibe config is **local-only**; not shared with Devin

### 4. Claude Code

- Global: `~/.claude/settings.json`
- Repo: `AGENTS.md` / `CLAUDE.md`
- Action: shell policy in repo docs; hooks remain product-specific

### 5. Codex

- Global: `~/.codex/config.toml`
- Action: same shell policy section in `AGENTS.md`
- MCP/server config is separate from shell launcher

### 6. Devin (cloud)

- Repo: `.devin/` (initialize + maintenance on **Ubuntu**)
- Local companion: `.devin/rules/agent-shell.md`, hooks, rules
- Remote shell is system bash/sh — **no Fish**, no `~/bin/agent-zsh` unless you
  install it in the VM
- Action: keep blueprint POSIX-only; document local vs cloud differences

### 7. Antigravity / Gemini

- Local IDE settings under Application Support (separate from Cursor)
- Repo hints: `AGENTS.md`, agent rules
- Action: document in repo agent guides; cloud/IDE sides still differ

### 8. Raycast

- **Script Commands:** interpreter comes from the script shebang (`bash`,
  `zsh`, `osascript`). They do **not** use Fish unless the shebang says so.
- **AI Terminal:** runs commands in a shell on this Mac. Prefer
  `agent-zsh -c '…'` from AI instructions, or a Script Command wrapper.
- Details: [`docs/RAYCAST_AGENT_SHELL.md`](RAYCAST_AGENT_SHELL.md)

## Sync vs separate

| Artifact                 | Cursor IDE               | Local CLIs    | Devin cloud              | Raycast                |
| :----------------------- | :----------------------- | :------------ | :----------------------- | :--------------------- |
| `agent-zsh` launchers    | optional default profile | prefix / PATH | install in VM if desired | shebang or wrapper     |
| shell policy in repo     | yes                      | yes           | yes (guidance)           | yes (if AI reads repo) |
| IDE terminal profile     | yes                      | no            | no                       | no                     |
| `.devin` blueprint       | no                       | no            | yes                      | no                     |
| Vibe config              | no                       | Vibe only     | no                       | no                     |
| Script Command shebang   | no                       | no            | no                       | yes                    |

## Recommended operator checklist

1. Keep login shell = Fish
2. Keep `agent-zsh` / `agent-bash` on `PATH` (for example `~/bin`)
3. Optionally set Cursor default + automation profile to `agent-zsh`
4. Repo mandates prefix via `AGENTS.md` / `.cursor/rules/agent-shell.mdc`
5. Vibe/Claude/Codex instructions mirror the same rule
6. Devin blueprint stays Ubuntu/bash
7. Raycast scripts use bash/zsh shebang (or call `agent-zsh`)
8. Run `agent-term-doctor` after launcher or profile changes

## Quick verification

```bash
command -v agent-zsh agent-bash
agent-shell-selftest
agent-term-doctor
agent-zsh -c 'pwd; git --no-pager rev-parse --is-inside-work-tree'
```
