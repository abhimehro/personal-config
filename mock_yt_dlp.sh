#!/bin/bash
# Mock yt-dlp to inspect arguments
echo "Mock yt-dlp called with $# arguments"
index=1
for arg in "$@"; do
  echo "ARG $index: $arg"
  if [[ "$arg" == "--exec" ]]; then
      echo "⚠️  VULNERABILITY TRIGGERED: --exec flag detected!"
  fi
  if [[ "$arg" == --exec* ]]; then
      echo "⚠️  VULNERABILITY TRIGGERED: --exec option detected!"
  fi
  ((index++))
done
