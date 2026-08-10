#!/bin/bash
# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Agent Zsh Run
# @raycast.mode fullOutput
# @raycast.packageName Agent Shell
# @raycast.description Run a command in agent-zsh (POSIX), not Fish
# @raycast.author Abhi Mehrotra
# @raycast.argument1 { "type": "text", "placeholder": "command", "percentEncoded": false }

set -euo pipefail
CMD="${1:-}"
if [[ -z $CMD ]]; then
	echo "usage: provide a command" >&2
	exit 2
fi
exec "$HOME/bin/agent-zsh" -c "$CMD"
