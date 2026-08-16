# Agent shell (Fish stays login)

Isolated POSIX shells for coding agents so they do not evaluate Fish syntax.

## Launchers

| Command                | Purpose                                               |
| :--------------------- | :---------------------------------------------------- |
| `agent-zsh`            | Primary agent shell (`ZDOTDIR=~/.config/agent-shell`) |
| `agent-bash`           | Fallback (`BASH_ENV` + `--rcfile`)                    |
| `agent-term-doctor`    | Session-start health check + postmortem log           |
| `agent-session`        | Runs doctor, then opens `agent-zsh`                   |
| `agent-shell-selftest` | Quick launcher self-check                             |

## Do agents auto-use this?

**No.** AI agents do **not** automatically switch away from your Fish login
shell.

They use whatever shell the **host tool** starts:

- Raycast AI Terminal / shell tools
- Cursor / VS Code integrated terminal + agent terminals
- Claude Code / Codex / other CLI agents

Unless that tool is configured to start `agent-zsh` (or you prefix commands),
the agent often lands in **Fish** or a bare system shell.

### What you should do

1. **Prefer explicit commands in agent instructions**
   ```bash
   agent-zsh -c "git status -sb"
   # fallback
   agent-bash -c "git status -sb"
   ```
2. **Session start**
   ```bash
   agent-term-doctor
   # or
   agent-session
   ```
3. **Optional per-product defaults**
   - Cursor/VS Code: set terminal default profile / automation profile to
     `agent-zsh`
   - Claude/Codex project docs (`AGENTS.md` / `CLAUDE.md`): tell the agent to
     run via `agent-zsh -c`
   - Do **not** change your macOS login shell away from Fish

## Doctor logs

```text
~/.local/state/agent-term-doctor/session-<utc>-<pid>.log
~/.local/state/agent-term-doctor/latest.log
~/.local/state/agent-term-doctor/latest.json
```

```bash
agent-term-doctor           # human output + log
agent-term-doctor --quiet   # prints log path only
agent-term-doctor --json    # machine summary
agent-term-doctor --print-log
```

## Why this exists

Agents often break on Fish and often start with `cwd=/` plus non-TTY stdio. This
config:

1. Forces a clean PATH
2. Sets `PYTHONUNBUFFERED=1` and `PAGER=cat`
3. Auto-cds to `$AGENT_WORKSPACE` from `/` or `$HOME`
4. Loads bash env on non-interactive `bash -c` via `BASH_ENV`

## Product matrix (what syncs vs what does not)

| Surface                | Config location                                                                                    | Shell control                                                              | Syncs with others?                            |
| :--------------------- | :------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------- | :-------------------------------------------- |
| Cursor IDE             | `~/Library/Application Support/Cursor/User/settings.json` + workspace `.vscode/settings.json`      | `terminal.integrated.*Profile*` / `automationProfile`                      | No. IDE-only                                  |
| Antigravity IDE        | `~/Library/Application Support/Antigravity/User/settings.json` + workspace `.vscode/settings.json` | Same VS Code-style keys                                                    | No. Separate app settings                     |
| Cursor CLI (`agent`)   | `~/.cursor/cli-config.json`                                                                        | No shell binary key today; inherits process env / explicit commands        | Separate from IDE UI attribution/settings     |
| Devin CLI (local)      | `~/.config/devin/config.json`, rules/skills                                                        | Local exec on your Mac; prefer `agent-zsh -c` via rules                    | Does **not** reconfigure Devin Cloud VM shell |
| Devin Cloud            | Web/cloud environment                                                                              | Cloud VM/image setup (`devin cloud` / env setup)                           | Separate from local macOS shell               |
| Mistral Vibe           | `~/.vibe/config.toml`, `~/.vibe/AGENTS.md`                                                         | `tools.bash` permissions/allowlist; still invoke `agent-zsh -c`            | Local only                                    |
| Raycast AI shell tools | Extension runtime / Script Commands                                                                | Uses shebang or explicit launcher; AI terminal tools follow host/extension | Separate from IDE                             |
| Claude Code / Codex    | `~/.claude/settings.json`, `~/.codex/config.toml`, repo `AGENTS.md`/`CLAUDE.md`                    | Instruction-level + hooks; not a shared IDE terminal profile               | Separate                                      |

### Practical rule

- **IDE terminal profiles** only affect that IDE’s integrated/automation
  terminals.
- **CLI agents** need either (a) explicit `agent-zsh -c` in prompts/rules, or
  (b) a product-specific shell setting if it exists.
- **Cloud agents** never read your local `~/bin/agent-zsh` unless you install
  equivalent tooling in the remote environment.

## Raycast

Import Script Commands from your scripts folder (or add the folder in Raycast →
Extensions → Script Commands):

- `agent-zsh-run.sh`
- `agent-term-doctor.sh`
- `agent-session.sh`

For AI chats that execute shell tools, prefer asking: “run via `agent-zsh -c`”.

## Full host matrix

See
[`docs/AGENT_SHELL_CONFIG_MATRIX.md`](../../../docs/AGENT_SHELL_CONFIG_MATRIX.md)
for Cursor, Vibe, Claude, Codex, Devin, Antigravity, and Raycast.
