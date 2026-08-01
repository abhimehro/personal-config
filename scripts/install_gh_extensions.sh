#!/usr/bin/env bash
# Installs (or verifies) the gh CLI extensions this repo relies on.
# Idempotent: safe to run repeatedly. Mirrors the check pattern used in
# secops/phase1-workflow-updater.sh ("gh extension list | grep -q ...").
#
# Usage: scripts/install_gh_extensions.sh

set -Eeuo pipefail

# name -> source repo, one pair per line: "extension-name owner/repo"
GH_EXTENSIONS=(
	"gh-aw github/gh-aw"
	"gh-codeql github/gh-codeql"
	"gh-copilot github/gh-copilot"
	"gh-models github/gh-models"
	"gh-prism kawarimidoll/gh-prism"
	"gh-stack github/gh-stack"
	"gh-webhook cli/gh-webhook"
)

if ! command -v gh >/dev/null 2>&1; then
	echo "error: gh CLI not found. Install it first (brew bundle --file=macos/Brewfile)." >&2
	exit 1
fi

installed="$(gh extension list 2>/dev/null || true)"

for entry in "${GH_EXTENSIONS[@]}"; do
	name="${entry%% *}"
	repo="${entry#* }"
	if echo "$installed" | grep -q "$name"; then
		echo "  ok: $name already installed"
		continue
	fi
	echo "  installing: $repo"
	if gh extension install "$repo"; then
		echo "  ok: $name installed"
	else
		echo "  warn: failed to install $name ($repo)" >&2
	fi
done
