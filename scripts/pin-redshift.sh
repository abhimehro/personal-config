#!/usr/bin/env bash
# pin-redshift.sh — pin the deprecated redshift formula so `brew upgrade` leaves
# the working install alone, and keep README.md's "Pinned Formulae" section in
# sync (version, pin date, disable date, and the cache-path note).
#
# Why: the core `redshift` formula is deprecated (upstream unmaintained; last
# release 1.12) and Homebrew has it scheduled for *disable* on 2027-06-21.
# Pinning protects through the deprecation window only — see the README escape
# hatch for the post-disable, from-source path.
#
# Usage:
#   ./scripts/pin-redshift.sh           # pin + refresh the README block
#   ./scripts/pin-redshift.sh --fetch   # also cache the bottle and record its path
set -euo pipefail

FORMULA="redshift"
DISABLE_DATE="2027-06-21"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
README="${ROOT}/README.md"

PIN_START="<!-- PINNED-FORMULAE:START -->"
PIN_END="<!-- PINNED-FORMULAE:END -->"
CACHE_START="<!-- REDSHIFT-CACHE-PATH:START -->"
CACHE_END="<!-- REDSHIFT-CACHE-PATH:END -->"

do_fetch=0
[[ ${1-} == "--fetch" ]] && do_fetch=1

# --- preconditions ----------------------------------------------------------
if ! command -v brew >/dev/null 2>&1; then
	echo "error: Homebrew (brew) is not installed or not on PATH." >&2
	exit 1
fi

# Note: use `brew list --versions` rather than `brew list --formula | grep -q`.
# Under `set -o pipefail`, `grep -q` closes the pipe on first match, killing
# `brew list` with SIGPIPE (~141) and poisoning the pipeline's exit status.
if ! brew list --versions "$FORMULA" >/dev/null 2>&1; then
	echo "error: $FORMULA is not installed via brew — nothing to pin." >&2
	exit 1
fi

# --- gather facts -----------------------------------------------------------
VERSION="$(brew list --versions "$FORMULA" | awk '{print $2}')"
echo "Found $FORMULA $VERSION"

# Preserve an existing pin date if one is already recorded; otherwise use today,
# so re-running the script does not churn the original pin date.
PIN_DATE=""
if [[ -f $README ]]; then
	PIN_DATE="$(awk -v s="$PIN_START" -v e="$PIN_END" '
		index($0, s) {f=1; next} index($0, e) {f=0} f' "$README" |
		grep -Eo '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1 || true)"
fi
[[ -z $PIN_DATE ]] && PIN_DATE="$(date +%F)"

# --- pin --------------------------------------------------------------------
brew pin "$FORMULA"
# Capture first, then grep a here-string — same pipefail/SIGPIPE reasoning.
pinned_list="$(brew list --pinned)"
if grep -qx "$FORMULA" <<<"$pinned_list"; then
	echo "✅ $FORMULA $VERSION is pinned (safe from brew upgrade)."
else
	echo "⚠️  Pin did not register — check 'brew list --pinned' manually." >&2
	exit 1
fi

# --- resolve (and optionally populate) the cache artifact -------------------
CACHE_PATH="$(brew --cache "$FORMULA" 2>/dev/null || true)"
if [[ $do_fetch -eq 1 ]]; then
	echo "Fetching bottle into the Homebrew cache..."
	brew fetch "$FORMULA" >/dev/null
	CACHE_PATH="$(brew --cache "$FORMULA" 2>/dev/null || true)"
fi

# --- copy-paste-ready output (always, even if README markers are missing) ----
ROW="| ${FORMULA} | ${VERSION} | ${PIN_DATE} | ${DISABLE_DATE} |"
echo
echo "Copy-paste-ready entry:"
echo "  ${ROW}"
[[ -n $CACHE_PATH ]] && echo "  cache: ${CACHE_PATH}"
echo

# --- splice README managed blocks -------------------------------------------
splice_block() {
	local file="$1" start="$2" end="$3" content_file="$4" tmp
	tmp="$(mktemp)"
	awk -v s="$start" -v e="$end" -v cf="$content_file" '
		index($0, s) {
			print
			while ((getline line < cf) > 0) print line
			close(cf)
			skip = 1
			next
		}
		index($0, e) { skip = 0; print; next }
		!skip { print }
	' "$file" >"$tmp" && mv "$tmp" "$file"
}

if [[ ! -f $README ]]; then
	echo "note: $README not found; skipped README update."
	exit 0
fi

if ! grep -qF "$PIN_START" "$README"; then
	echo "note: '$PIN_START' marker not found in README; skipped auto-update."
	echo "      Add the Pinned Formulae section once, then re-run to keep it synced."
	exit 0
fi

pin_tmp="$(mktemp)"
{
	echo "" # blank lines keep markdownlint (MD031/MD032) happy on re-runs
	echo "| Formula  | Version | Pinned (date) | Disable date |"
	echo "| -------- | ------- | ------------- | ------------ |"
	echo "$ROW"
	echo ""
} >"$pin_tmp"
splice_block "$README" "$PIN_START" "$PIN_END" "$pin_tmp"
rm -f "$pin_tmp"

if grep -qF "$CACHE_START" "$README"; then
	cache_tmp="$(mktemp)"
	if [[ -n $CACHE_PATH ]]; then
		{
			echo ""
			echo "- Cached bottle artifact (lives **outside** this repo — do not commit):"
			echo "  \`${CACHE_PATH}\`"
			echo ""
		} >"$cache_tmp"
	else
		{
			echo ""
			# shellcheck disable=SC2016 # literal backticks for markdown; no expansion wanted
			echo '- Cached bottle artifact: run `scripts/pin-redshift.sh --fetch` to populate this path.'
			echo ""
		} >"$cache_tmp"
	fi
	splice_block "$README" "$CACHE_START" "$CACHE_END" "$cache_tmp"
	rm -f "$cache_tmp"
fi

echo "✅ README Pinned Formulae section updated."
