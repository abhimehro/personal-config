#!/bin/bash
# YouTube downloader script for SearchJumper integration
# Downloads videos to ~/Downloads with best quality

URL="$1"

# Security: Validate input
if [[ -z "$URL" ]]; then
  echo "Error: No URL provided."
  echo "Usage: youtube-download.sh <url>"
  exit 1
fi

# Improved URL validation: require protocol, domain, and anchor pattern
if [[ ! "$URL" =~ ^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}([:/?#][^\s]*)?$ ]]; then
  echo "Error: Invalid URL. Must be a valid http(s) URL with a domain."
  exit 1
fi

# Use -- to prevent argument injection
/opt/homebrew/bin/yt-dlp -o "$HOME/Downloads/%(title)s.%(ext)s" -- "$URL"
YTDLP_EXIT_CODE=$?
if [[ $YTDLP_EXIT_CODE -ne 0 ]]; then
  echo "Error: yt-dlp failed to download the video (exit code $YTDLP_EXIT_CODE). Please check the URL, your network connection, and that yt-dlp is installed."
  exit $YTDLP_EXIT_CODE
fi

# Optional: Show notification when complete (requires terminal-notifier)
# brew install terminal-notifier
# terminal-notifier -title "Download Complete" -message "Video saved to Downloads"
