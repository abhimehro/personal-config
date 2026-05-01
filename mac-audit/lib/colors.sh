#!/usr/bin/env bash
# lib/colors.sh — ANSI color helpers
# shellcheck disable=SC2034
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'
pass() { printf "${GREEN}[PASS]${RESET}  %s\n" "$*"; }
warn() { printf "${YELLOW}[WARN]${RESET}  %s\n" "$*"; }
fail() { printf "${RED}[FAIL]${RESET}  %s\n" "$*"; }
info() { printf "${CYAN}[INFO]${RESET}  %s\n" "$*"; }
header() { printf "\n${BOLD}━━━ %s ━━━${RESET}\n" "$*"; }
