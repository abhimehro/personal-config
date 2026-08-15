# Raycast + agent-zsh

## Script Commands

- Interpreter = shebang (use `#!/bin/bash` or `#!/bin/zsh`, not Fish)
- Directory: add your Script Commands folder via Settings → Extensions → Script
  Commands
- Does not read Cursor terminal profiles

Suggested wrappers (if present in your Raycast scripts folder):

- `agent-zsh-run.sh`
- `agent-term-doctor.sh`
- `agent-session.sh`

## AI Terminal

Raycast AI can run shell commands on this Mac. To avoid Fish:

1. Prefix commands with `agent-zsh -c '…'`
2. Or use a Script Command that invokes `agent-zsh`

## Suggested AI Extension custom instruction

Settings → AI Extensions → Terminal → Custom Instructions:

```text
Prefer agent-zsh -c '<command>' for shell tools.
Fallback: agent-bash -c '<command>'.
Do not change the macOS login shell away from Fish.
Do not emit raw Fish syntax.
```

## Permissions

Grant Accessibility/Automation/FDA prompts to **Raycast**, not Terminal.
