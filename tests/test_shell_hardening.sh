#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WATCHDOG="$REPO_ROOT/scripts/report-daemons-watchdog.sh"
APPS_MODULE="$REPO_ROOT/configs/.config/mole/lib/clean/apps.sh"
USER_MODULE="$REPO_ROOT/configs/.config/mole/lib/clean/user.sh"
TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/personal-config-shell-hardening.XXXXXX")"
TEST_HOME="$TEST_ROOT/home"
MOCK_ENV="$TEST_ROOT/mock-env.sh"
PGREP_LOG="$TEST_ROOT/pgrep.log"

cleanup() { rm -rf "$TEST_ROOT"; }
trap cleanup EXIT
mkdir -p "$TEST_HOME"

cat >"$MOCK_ENV" <<'MOCK'
pgrep() {
  printf 'pgrep' >>"$PGREP_LOG"
  local argument
  for argument in "$@"; do
    printf ' <%s>' "$argument" >>"$PGREP_LOG"
  done
  printf '\n' >>"$PGREP_LOG"
  return 1
}
MOCK

assert_contains() {
  local expected="$1"
  local file="$2"
  grep -Fqx -- "$expected" "$file" || {
    printf 'expected line not found: %s\n' "$expected" >&2
    cat "$file" >&2
    exit 1
  }
}

assert_shopt_state_restoration() {
  local module="$1"
  local marker="$TEST_ROOT/should-not-exist"
  HOME="$TEST_HOME" bash -c '
    set -euo pipefail
    source "$1"
    shopt -u nullglob dotglob
    _restore_shopt_state "shopt -s nullglob" nullglob
    shopt -q nullglob
    _restore_shopt_state "shopt -s dotglob" dotglob
    shopt -q dotglob
    _restore_shopt_state "shopt -u nullglob" nullglob
    ! shopt -q nullglob
    _restore_shopt_state "shopt -u dotglob" dotglob
    ! shopt -q dotglob
    _restore_shopt_state "shopt -s nullglob; touch $2" nullglob
    [[ ! -e $2 ]]
    _restore_shopt_state "shopt -s extglob" nullglob
    ! shopt -q nullglob
  ' bash "$module" "$marker"
}

assert_shopt_state_restoration "$APPS_MODULE"
assert_shopt_state_restoration "$USER_MODULE"

PGREP_LOG="$PGREP_LOG" HOME="$TEST_HOME" BASH_ENV="$MOCK_ENV" bash -c '
  source "$1"
  check_stuck --leading-dash-process
' bash "$WATCHDOG"

assert_contains 'pgrep <-x> <--> <ReportCrash>' "$PGREP_LOG"
assert_contains 'pgrep <-x> <--> <ReportCrashService>' "$PGREP_LOG"
assert_contains 'pgrep <-x> <--> <ReportMemoryException>' "$PGREP_LOG"
assert_contains 'pgrep <-x> <--> <--leading-dash-process>' "$PGREP_LOG"

printf 'PASS: shell hardening regressions\n'
