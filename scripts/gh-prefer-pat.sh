#!/usr/bin/env bash
# Prefer the injected human PAT (GH_TOKEN) for gh issue/PR lifecycle writes.
# SECURITY: Cursor Cloud may also expose a hosts.yml ghs_ App token as
# cursor[bot]. That token can create issues but still 403 on comment/close
# even when the App install UI shows Issues R/W (Lesson 0fn). Unsetting
# GH_TOKEN forces the reduced App token — avoid that for Daily QA closes.
set -euo pipefail

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo "error: GH_TOKEN is unset; cannot use PAT lifecycle path" >&2
  exit 1
fi

login="$(gh api user --jq .login 2>/dev/null || true)"
if [[ -z "${login}" ]]; then
  echo "error: GH_TOKEN present but gh api user failed" >&2
  exit 1
fi

echo "gh identity: ${login} (PAT path; GH_TOKEN kept set)"
exec gh "$@"
