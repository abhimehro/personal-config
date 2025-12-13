#!/bin/bash
# YouTube downloader script for SearchJumper integration
# Downloads videos to ~/Downloads with best quality

URL="$1"

# Security: Validate input
if [[ -z "$URL" ]]; then
  echo "Error: No URL provided"
  exit 1
fi

# Improved URL validation: require protocol, domain, and anchor pattern
if [[ ! "$URL" =~ ^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}([:/?#][^\s]*)?$ ]]; then
  echo "Error: Invalid URL. Must be a valid http(s) URL with a domain."
  exit 1
fi

# Use -- to prevent argument injection
/opt/homebrew/bin/yt-dlp -o "$HOME/Downloads/%(title)s.%(ext)s" -- "$URL"

# Optional: Show notification when complete (requires terminal-notifier)
# brew install terminal-notifier
# terminal-notifier -title "Download Complete" -message "Video saved to Downloads"
