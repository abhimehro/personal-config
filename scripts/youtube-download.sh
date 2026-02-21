#!/bin/bash
# YouTube downloader script for SearchJumper integration
# Downloads videos to ~/Downloads with best quality

set -euo pipefail

# --- UX Helpers ---

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Emojis 🎨
E_INFO="ℹ️"
E_OK="✅"
E_WARN="⚠️"
E_ERR="❌"
E_BOLT="⚡"
E_VIDEO="🎬"
E_DOWN="⬇️"
E_SEARCH="🔍"

info()  { echo -ne "${BLUE}${E_INFO}  [INFO]${NC}  "; printf "%s\n" "$*"; }
ok()    { echo -ne "${GREEN}${E_OK} [OK]${NC}    "; printf "%s\n" "$*"; }
warn()  { echo -ne "${YELLOW}${E_WARN}  [WARN]${NC}  "; printf "%s\n" "$*"; }
err()   { echo -ne "${RED}${E_ERR} [ERR]${NC}   "; printf "%s\n" "$*" >&2; }
header() { echo -ne "\n${BOLD}${BLUE}"; printf "%s" "$*"; echo -e "${NC}\n"; }

# --- Usage ---

print_usage() {
  echo -e "${BOLD}YouTube Downloader${NC}"
  echo -e "Downloads videos to ~/Downloads with best quality + aria2c acceleration."
  echo -e ""
  echo -e "Usage: $(basename "$0") <url>"
  echo -e ""
  echo -e "Example:"
  echo -e "  $(basename "$0") \"https://www.youtube.com/watch?v=dQw4w9WgXcQ\""
}

# --- Main ---

URL="${1:-}"

if [[ "$URL" == "-h" ]] || [[ "$URL" == "--help" ]]; then
  print_usage
  exit 0
fi

# Interactive mode if no URL provided and running in terminal
if [[ -z "$URL" ]] && [[ -t 0 ]]; then
  # Try to detect from clipboard (macOS)
  if command -v pbpaste >/dev/null 2>&1; then
    CLIP_CONTENT=$(pbpaste)
    # Simple heuristic for YouTube URLs
    if [[ "$CLIP_CONTENT" =~ ^https?://(www\.)?(youtube\.com|youtu\.be)/ ]]; then
      echo -ne "${YELLOW}${E_SEARCH} Found in clipboard: ${BOLD}"; printf "%s" "$CLIP_CONTENT"; echo -e "${NC}"
      read -p "Use this URL? [Y/n] " -n 1 -r REPLY
      echo "" # Newline
      if [[ -z "$REPLY" ]] || [[ "$REPLY" =~ ^[Yy]$ ]]; then
        URL="$CLIP_CONTENT"
      fi
    fi
  fi

  # Prompt if still empty
  if [[ -z "$URL" ]]; then
    echo -e "${BLUE}${E_SEARCH} Please enter the YouTube URL:${NC}"
    read -r URL
  fi
fi

if [[ -z "$URL" ]]; then
  print_usage
  exit 1
fi

header "${E_VIDEO} YouTube Downloader"

# 1. Validation
info "Validating URL..."
if [[ ! "$URL" =~ ^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}([:/?#][^\s]*)?$ ]]; then
  err "Invalid URL. Must be a valid http(s) URL with a domain."
  exit 1
fi
ok "URL looks valid."

# 2. Dependency Checks
info "Checking dependencies..."

# Resolve yt-dlp path
YTDLP_CMD="yt-dlp"
if ! command -v "$YTDLP_CMD" >/dev/null 2>&1; then
  if [[ -x "/opt/homebrew/bin/yt-dlp" ]]; then
    YTDLP_CMD="/opt/homebrew/bin/yt-dlp"
  else
    err "yt-dlp not found. Please install it: brew install yt-dlp"
    exit 1
  fi
fi
ok "Found yt-dlp at $YTDLP_CMD"

# Check aria2c
EXTERNAL_DOWNLOADER_ARGS=()
if command -v aria2c >/dev/null 2>&1; then
  ok "Found aria2c for acceleration"
  # -x8: 8 connections per server
  # -s8: 8 splits/sources per download
  # -k1M: 1MB split size
  info "${E_BOLT} Speed boost enabled (8 connections)"
  EXTERNAL_DOWNLOADER_ARGS=(--downloader aria2c --downloader-args "aria2c:-c -x8 -s8 -k1M")
else
  warn "aria2c not found. Downloading will be slower."
  info "Install aria2c for speed: brew install aria2c"
fi

# 3. Execution
header "${E_DOWN} Starting Download"

info "Target: $URL"
info "Output: ~/Downloads"

# Use -- to prevent argument injection
"$YTDLP_CMD" "${EXTERNAL_DOWNLOADER_ARGS[@]}" -o "$HOME/Downloads/%(title)s.%(ext)s" -- "$URL"
YTDLP_EXIT_CODE=$?

if [[ $YTDLP_EXIT_CODE -ne 0 ]]; then
  err "Download failed (exit code $YTDLP_EXIT_CODE)."
  info "Please check the URL, your network connection, and update yt-dlp."
  exit $YTDLP_EXIT_CODE
fi

# 4. Summary
header "${E_OK} Download Complete"
info "Video saved to ~/Downloads"

# Optional: Notification
if command -v terminal-notifier >/dev/null 2>&1; then
  terminal-notifier -title "Download Complete" -message "Video saved to Downloads"
fi
