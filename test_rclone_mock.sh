#!/bin/bash
RCLONE_LOG="test.log"
if [[ "$1" == "serve" ]]; then
  while [[ $# -gt 0 ]]; do
    case $1 in
      --user) echo "USER=$2" >> "$RCLONE_LOG"; shift 2 ;;
      --pass) echo "PASS=$2" >> "$RCLONE_LOG"; shift 2 ;;
      *) shift ;;
    esac
  done
fi
