#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Agent Term Doctor
# @raycast.mode fullOutput
# @raycast.packageName Agent Shell

# Optional parameters:
# @raycast.icon 🩺
# @raycast.description Run agent-term-doctor health checks for POSIX agent shells

set -euo pipefail
export PATH="/Users/speedybee/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/Users/speedybee/.local/state/fnm_multishells/97845_1785865107976/bin:/opt/homebrew/opt/trash/bin:/Users/speedybee/.codeium/windsurf/bin:/Users/speedybee/.antigravity-ide/antigravity-ide/bin:/Users/speedybee/scripts:/Users/speedybee/bin:/Users/speedybee/.local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/Users/speedybee/.config/kaku/fish/bin:/usr/local/bin:/System/Cryptexes/App/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/local/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/appleinternal/bin:/pkg/env/global/bin:/Library/Apple/usr/bin:/Users/speedybee/.local/state/fnm_multishells/97845_1785865107976/bin:/opt/homebrew/opt/trash/bin:/Users/speedybee/.codeium/windsurf/bin:/Users/speedybee/.antigravity-ide/antigravity-ide/bin:/Users/speedybee/scripts:/Users/speedybee/bin:/Users/speedybee/.local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/Users/speedybee/.config/kaku/fish/bin:/usr/local/bin:/System/Cryptexes/App/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/local/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/appleinternal/bin:/pkg/env/global/bin:/Library/Apple/usr/bin"
if [[ -x "/Users/speedybee/bin/agent-term-doctor" ]]; then
  exec "/Users/speedybee/bin/agent-term-doctor"
fi
echo "agent-term-doctor not found in ~/bin" >&2
exit 127
