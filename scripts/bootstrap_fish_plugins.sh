#!/usr/bin/env bash
#
# Bootstrap Fish plugins (Option A)
# - Installs Fisher if missing
# - Runs `fisher update` using the repo-managed `~/.config/fish/fish_plugins`
#
# Usage:
#   ./scripts/bootstrap_fish_plugins.sh
#
set -Eeuo pipefail

if ! command -v fish >/dev/null 2>&1; then
  echo "Error: fish is not installed or not in PATH." >&2
  exit 1
fi

# Use a login shell so PATH is consistent with the user's environment.
fish -lc '
if not type -q fisher
    echo "Bootstrapping Fisher..." >&2

    if not type -q curl
        echo "Error: curl is required to install Fisher." >&2
        exit 1
    end

    # Install Fisher from the official repository.
    curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source
    fisher install jorgebucaran/fisher
end

fisher update
'

