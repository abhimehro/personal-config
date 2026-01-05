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

# Colors and logging (consistent with setup.sh)
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${BLUE}ℹ️  [INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}✅ [OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}⚠️  [WARN]${NC}  $*"; }
err()   { echo -e "${RED}❌ [ERR]${NC}   $*" >&2; }

info "Checking for Fish shell..."

if ! command -v fish >/dev/null 2>&1; then
  err "fish is not installed or not in PATH."
  exit 1
fi

ok "Fish shell found."
info "Bootstrapping Fisher and plugins..."

# Use a login shell so PATH is consistent with the user's environment.
# We also define helper functions inside fish for consistent output.
fish -lc '
function info
    set_color blue; echo "ℹ️  [INFO] $argv"; set_color normal
end

function ok
    set_color green; echo "✅ [OK]    $argv"; set_color normal
end

function warn
    set_color yellow; echo "⚠️  [WARN]  $argv"; set_color normal
end

function err
    set_color red; echo "❌ [ERR]   $argv" >&2; set_color normal
end

if not type -q fisher
    info "Fisher not found. Installing..."

    if not type -q curl
        err "curl is required to install Fisher."
        exit 1
    end

    # Install Fisher from the official repository.
    curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source
    fisher install jorgebucaran/fisher
    ok "Fisher installed."
else
    info "Fisher is already installed."
end

info "Updating plugins via Fisher..."
fisher update
ok "Fish plugins updated successfully."
'

ok "Bootstrap complete!"
