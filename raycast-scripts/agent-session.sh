#!/bin/bash
# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Agent Session (zsh)
# @raycast.mode fullOutput
# @raycast.packageName Agent Shell
# @raycast.description Run doctor then open a one-shot agent-zsh status shell
# @raycast.author Abhi Mehrotra

set -euo pipefail
"$HOME/bin/agent-term-doctor" || true
exec "$HOME/bin/agent-zsh" -c 'echo "agent-zsh ready"; echo "PWD=$PWD"; echo "SHELL_BIN=agent-zsh"; git rev-parse --is-inside-work-tree 2>/dev/null || true'
