# Raycast Script Commands, Agent Shell

Local Script Commands for Raycast, used to run agent tooling in a POSIX shell
instead of Fish.

## Setup

1. Open **Settings, Extensions, Script Commands**.
2. Click **Add Script Directory** and choose `~/dev/personal-config/raycast-scripts`.
3. The commands below appear in Root Search.

## Scripts

| Script                 | Command             | Purpose                                                  |
| :--------------------- | :------------------ | :------------------------------------------------------- |
| `agent-session.sh`     | Agent Session (zsh) | Run doctor, then open a one-shot agent-zsh status shell  |
| `agent-term-doctor.sh` | Agent Term Doctor   | Run agent-term-doctor health checks for POSIX shells     |
| `agent-zsh-run.sh`     | Agent Zsh Run       | Run a command in agent-zsh (POSIX), not Fish             |
| `agent-zsh-status.sh`  | Agent Zsh Self-Test | Verify agent-zsh launcher env (PATH, PAGER, workspace)   |
| `run-in-agent-zsh.sh`  | Run in Agent Zsh    | Run a command inside `agent-zsh -c` (avoids Fish)        |
| `kaset-play-pause.sh`  | Play/Pause Kaset    | Toggle play/pause in the Kaset YouTube Music player      |

## agent-zsh environment

The launcher sets the following for every command it runs:

```text
shell=zsh
ZDOTDIR=/Users/speedybee/.config/agent-shell
PWD=/Users/speedybee/dev/abhimehro
AGENT_WORKSPACE=/Users/speedybee/dev/abhimehro
PYTHONUNBUFFERED=1
PAGER=cat
```

## Why shebangs matter

Raycast runs Script Commands with the interpreter named in the shebang
(`#!/bin/bash` here). They do **not** use your Fish login shell unless the
shebang points at Fish.

## AI Terminal tip

When using Raycast AI `@terminal`, prefer:

```bash
agent-zsh -c "your command here"
```

Or run the **Run in Agent Zsh** Script Command.
