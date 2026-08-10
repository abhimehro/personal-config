# Agent shell configuration matrix

Last updated: 2026-08-04

This doc explains **what is shared**, **what is separate**, and **where to configure** each agent host so local Fish never breaks POSIX agent commands.

## Mental model

| Layer | What it controls | Shared across tools? | Fish risk |
|:---|:---|:---|:---|
| macOS login shell | Interactive human terminal (Fish) | OS-wide | N/A (intentional) |
|  +  | Clean POSIX env for agents | **Shared primitive** used by all local tools | None if used |
| IDE terminal profile (Cursor/VS Code/Windsurf) | Integrated terminal + often agent/automation shells | Per IDE user settings (not synced to cloud VMs) | High if default is Fish |
| Local CLI agents (Vibe, Claude Code, Codex, Cursor CLI, Antigravity CLI) | How the agent spawns shell tools on this Mac | Per-product config + repo  /  | High unless prefixed or IDE/default shell overridden |
| Cloud agents (Devin, cloud sandboxes) | Remote Linux VM shell | **Separate** ( / VM image) | Low (no Fish) |
| Raycast Script Commands / AI Terminal | Explicit shebang or Terminal extension command | Per script / per invocation | Low if shebang is bash/zsh |

**Key rule:** nothing auto-inherits  unless the **host tool** is configured to launch it, or the agent is instructed to prefix commands.

## Shared local primitive (configure once)

=== agent-term-doctor ===
log: /Users/speedybee/.local/state/agent-term-doctor/session-20260804T184634Z-28786.log
PASS  found agent-zsh -> /Users/speedybee/bin/agent-zsh
PASS  found agent-bash -> /Users/speedybee/bin/agent-bash
login_shell=unknown
WARN  could not read login shell
parent_comm=/bin/sh
PASS  agent-zsh workspace cd ok
PASS  agent-zsh unbuffered + pager hardened
PASS  agent-zsh stdout captured
PASS  agent-zsh stderr emitted
PASS  agent-bash workspace cd ok
PASS  agent-bash unbuffered + pager hardened
PASS  agent-bash stdout captured
PASS  agent-bash stderr emitted
PASS  agent-bash rc loaded on -c
burst agent-zsh 12/12
PASS  agent-zsh burst reliable
burst agent-bash 12/12
PASS  agent-bash burst reliable
PASS  git --no-pager returns output (0927973 fix: neutralize middle-dot in langs card alt text)
stdin_tty=no
stdout_tty=no
stderr_tty=no
----
INTERPRETATION
- PASS launchers + swallowed output later => suspect agent terminal tool/PTY, not shell rc
- Agents do NOT auto-switch from Fish; point them at agent-zsh or agent-bash
- Prefer: agent-zsh -c ...   fallback: agent-bash -c ...
----
summary warnings=1 failures=0
status=warn exit=1
latest=/Users/speedybee/.local/state/agent-term-doctor/latest.log
=== agent-term-doctor ===
log: /Users/speedybee/.local/state/agent-term-doctor/session-20260804T184635Z-28978.log
PASS  found agent-zsh -> /Users/speedybee/bin/agent-zsh
PASS  found agent-bash -> /Users/speedybee/bin/agent-bash
login_shell=unknown
WARN  could not read login shell
parent_comm=/bin/bash
NOTE  parent looks POSIX (/bin/bash)
PASS  agent-zsh workspace cd ok
PASS  agent-zsh unbuffered + pager hardened
PASS  agent-zsh stdout captured
PASS  agent-zsh stderr emitted
PASS  agent-bash workspace cd ok
PASS  agent-bash unbuffered + pager hardened
PASS  agent-bash stdout captured
PASS  agent-bash stderr emitted
PASS  agent-bash rc loaded on -c
burst agent-zsh 12/12
PASS  agent-zsh burst reliable
burst agent-bash 12/12
PASS  agent-bash burst reliable
PASS  git --no-pager returns output (0927973 fix: neutralize middle-dot in langs card alt text)
stdin_tty=no
stdout_tty=no
stderr_tty=no
----
INTERPRETATION
- PASS launchers + swallowed output later => suspect agent terminal tool/PTY, not shell rc
- Agents do NOT auto-switch from Fish; point them at agent-zsh or agent-bash
- Prefer: agent-zsh -c ...   fallback: agent-bash -c ...
----
summary warnings=1 failures=0
status=warn exit=1
latest=/Users/speedybee/.local/state/agent-term-doctor/latest.log

Managed copy (for version control / sync):



## Per-host configuration

### 1. Cursor IDE (local)
- **User settings:**
- **Workspace settings:**
- Set:
  -  =
  -  ->
  - profiles for , ,
- **Does not sync** to Devin/cloud VMs.
- Cursor CLI () is separate from IDE terminal profiles. CLI still needs  / explicit .

### 2. Cursor CLI
- Config:  (permissions, attribution, sandbox)
- Shell behavior: follows process environment + instructions in repo
- Action: keep allowlist broad enough for  / , and document prefix in

### 3. Mistral Vibe
- Config:
- Runs tools **locally**; bash tool often starts under login shell context
- Action:
  - Prefer commands via
  - Keep interactive shells denylisted (already present)
  - Optional: add  /  to bash allowlist prefixes
- Vibe config is **local-only**; not shared with Devin.

### 4. Claude Code
- Global: ,
- Repo:  /
- Action: shell policy in  + repo
- Hooks remain product-specific (1Password validate, LiveReview)

### 5. Codex
- Global: ,
- Action: same shell policy section in
- MCP/server config is separate from shell launcher

### 6. Devin (cloud)
- Repo:  (initialize + maintenance on **Ubuntu**)
- Local companion: , hooks, rules
- Remote shell is system / — **no Fish**, no  unless you install it in
- Action: keep blueprint POSIX-only; add knowledge notes for local vs cloud differences
- **Does not use** Cursor

### 7. Antigravity / Gemini
- Local state: ,
- Repo hints: ,  /
- CLI settings:  (editor, permissions; not macOS login shell)
- Action: document  in repo agent guides; cloud/IDE sides still differ

### 8. Raycast
- **Script Commands:** interpreter comes from the script shebang (, , ). They do **not** use Fish unless shebang says so.
- **AI Terminal ():** runs commands in a shell on this Mac. Prefer:
  -  from AI instructions, or
  - a Script Command wrapper that calls
- **AI Extensions custom instructions:** Settings -> extension -> Ask tool -> Custom Instructions
- Raycast does not read Cursor terminal profiles.

## Sync vs separate

| Artifact | Cursor IDE | Local CLIs | Devin cloud | Raycast |
|:---|:---|:---|:---|:---|
|  launchers | optional default profile | prefix / PATH | install in VM if desired | shebang or wrapper |
|  shell policy | yes (repo) | yes | yes (guidance) | yes (if AI reads repo) |
| IDE  terminal profile | yes | no | no | no |
|  | no | no | yes | no |
|  | no | Vibe only | no | no |
| Script Command shebang | no | no | no | yes |

## Recommended operator checklist

1. Keep login shell = Fish
2. Keep  on PATH ()
3. Cursor default + automation profile =
4. Repo  mandates
5. Vibe/Claude/Codex instructions mirror the same rule
6. Devin blueprint stays Ubuntu/bash
7. Raycast scripts use  or  (or call )
8. Run === agent-term-doctor ===
log: /Users/speedybee/.local/state/agent-term-doctor/session-20260804T184638Z-29292.log
PASS  found agent-zsh -> /Users/speedybee/bin/agent-zsh
PASS  found agent-bash -> /Users/speedybee/bin/agent-bash
login_shell=unknown
WARN  could not read login shell
parent_comm=/bin/sh
PASS  agent-zsh workspace cd ok
PASS  agent-zsh unbuffered + pager hardened
PASS  agent-zsh stdout captured
PASS  agent-zsh stderr emitted
PASS  agent-bash workspace cd ok
PASS  agent-bash unbuffered + pager hardened
PASS  agent-bash stdout captured
PASS  agent-bash stderr emitted
PASS  agent-bash rc loaded on -c
burst agent-zsh 12/12
PASS  agent-zsh burst reliable
burst agent-bash 12/12
PASS  agent-bash burst reliable
PASS  git --no-pager returns output (0927973 fix: neutralize middle-dot in langs card alt text)
stdin_tty=no
stdout_tty=no
stderr_tty=no
----
INTERPRETATION
- PASS launchers + swallowed output later => suspect agent terminal tool/PTY, not shell rc
- Agents do NOT auto-switch from Fish; point them at agent-zsh or agent-bash
- Prefer: agent-zsh -c ...   fallback: agent-bash -c ...
----
summary warnings=1 failures=0
status=warn exit=1
latest=/Users/speedybee/.local/state/agent-term-doctor/latest.log after changes

## Quick verification

agent-zsh self-test
shell=zsh
ZDOTDIR=/Users/speedybee/.config/agent-shell
PWD=/Users/speedybee/dev/abhimehro
AGENT_WORKSPACE=/Users/speedybee/dev/abhimehro
PYTHONUNBUFFERED=1
PAGER=cat
git=ok
python3=ok
stdout-mark
agent-bash self-test
shell=bash
BASH_ENV=/Users/speedybee/.config/agent-shell/bashrc
PWD=/Users/speedybee/dev/abhimehro
AGENT_WORKSPACE=/Users/speedybee/dev/abhimehro
PYTHONUNBUFFERED=1
PAGER=cat
git=ok
python3=ok
stdout-mark
=== agent-term-doctor ===
log: /Users/speedybee/.local/state/agent-term-doctor/session-20260804T184639Z-29473.log
PASS  found agent-zsh -> /Users/speedybee/bin/agent-zsh
PASS  found agent-bash -> /Users/speedybee/bin/agent-bash
login_shell=unknown
WARN  could not read login shell
parent_comm=/bin/sh
PASS  agent-zsh workspace cd ok
PASS  agent-zsh unbuffered + pager hardened
PASS  agent-zsh stdout captured
PASS  agent-zsh stderr emitted
PASS  agent-bash workspace cd ok
PASS  agent-bash unbuffered + pager hardened
PASS  agent-bash stdout captured
PASS  agent-bash stderr emitted
PASS  agent-bash rc loaded on -c
burst agent-zsh 12/12
PASS  agent-zsh burst reliable
burst agent-bash 12/12
PASS  agent-bash burst reliable
PASS  git --no-pager returns output (0927973 fix: neutralize middle-dot in langs card alt text)
stdin_tty=no
stdout_tty=no
stderr_tty=no
----
INTERPRETATION
- PASS launchers + swallowed output later => suspect agent terminal tool/PTY, not shell rc
- Agents do NOT auto-switch from Fish; point them at agent-zsh or agent-bash
- Prefer: agent-zsh -c ...   fallback: agent-bash -c ...
----
summary warnings=1 failures=0
status=warn exit=1
latest=/Users/speedybee/.local/state/agent-term-doctor/latest.log
