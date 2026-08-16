# Agent shell: local vs Devin cloud

## Cloud (this environment)

- OS shell is bash/sh on Ubuntu
- No Fish
- Prefer plain POSIX commands in blueprint / setup scripts

## Local workstation

- Login shell is Fish
- Use `agent-zsh -c '…'` or `agent-bash -c '…'` for agent commands
- See `AGENTS.md` (Agent shell section) and `docs/AGENT_SHELL_CONFIG_MATRIX.md`
