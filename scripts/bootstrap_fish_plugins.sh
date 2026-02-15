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

# Restore cursor on exit/interrupt
trap 'tput cnorm 2>/dev/null || true' EXIT INT TERM

# Spinner function (Palette 🎨 UX enhanced)
spinner() {
    local message="$1"
    shift
    local cmd="$*"

    # If not running in a TTY, just run the command without spinner
    if [ ! -t 1 ]; then
        info "$message..."
        eval "$cmd"
        return $?
    fi

    local pid
    local delay=0.1
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local start_time
    start_time=$(date +%s)
    local temp_log

    temp_log=$(mktemp)

    # Run command in background
    eval "$cmd" > "$temp_log" 2>&1 &
    pid=$!

    # Hide cursor
    tput civis 2>/dev/null || true

    local elapsed=0
    while kill -0 $pid 2>/dev/null; do
        local current_time
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        local temp=${spinstr#?}
        printf "\r${BLUE}%c${NC} %s (${elapsed}s)..." "$spinstr" "$message"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
    done

    wait $pid
    local exit_code=$?

    # Restore cursor (handled by trap too, but good to be explicit here for cleanliness)
    tput cnorm 2>/dev/null || true
    printf "\r\033[K"

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ [OK]${NC}    $message (Done in ${elapsed}s)"
    else
        echo -e "${RED}❌ [ERR]${NC}   $message (Failed)"
        echo -e "${RED}Error Output:${NC}"
        cat "$temp_log"
    fi
    rm "$temp_log"
    return $exit_code
}

info "Checking for Fish shell..."

if ! command -v fish >/dev/null 2>&1; then
  err "fish is not installed or not in PATH."
  exit 1
fi

ok "Fish shell found."

# 1. Check if Fisher is installed
if ! fish -lc 'type -q fisher'; then
    info "Fisher not found. Installing..."

    if ! command -v curl >/dev/null 2>&1; then
        err "curl is required to install Fisher."
        exit 1
    fi

    # Install Fisher
    spinner "Installing Fisher" "fish -lc 'curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source && fisher install jorgebucaran/fisher'"
else
    ok "Fisher is already installed."
fi

# 2. Update plugins
# We capture the output via spinner so user sees animation instead of raw output
# (unless it fails)
spinner "Updating plugins via Fisher" "fish -lc 'fisher update'"

ok "Bootstrap complete!"
