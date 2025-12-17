#!/bin/bash
# YouTube downloader script for SearchJumper integration
# Downloads videos to ~/Downloads with best quality

/opt/homebrew/bin/yt-dlp -o "$HOME/Downloads/%(title)s.%(ext)s" -- "$1"

# Optional: Show notification when complete (requires terminal-notifier)
# brew install terminal-notifier
# terminal-notifier -title "Download Complete" -message "Video saved to Downloads"
