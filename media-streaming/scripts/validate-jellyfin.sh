#!/usr/bin/env bash
# validate-jellyfin.sh — prove Jellyfin is up and can see CloudMedia content
#
# Exit codes:
#   0 = healthy enough for LAN use (HTTP up + mount readable + optional API items)
#   1 = hard failure (no HTTP / mount empty)
#   2 = soft: server up but wizard/auth not finished (expected pre-HITL)
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

BASE_URL="${JELLYFIN_URL:-http://127.0.0.1:8096}"
MOUNT_POINT="${JELLYFIN_MEDIA_ROOT:-$HOME/CloudMedia/mounted}"
API_KEY="${JELLYFIN_API_KEY-}" # optional; never commit real keys
TMP_BODY="$(mktemp)"
TMP_INFO="$(mktemp)"
trap 'rm -f "$TMP_BODY" "$TMP_INFO"' EXIT

pass=0
fail=0
soft=0

ok() {
	echo "✅ $*"
	pass=$((pass + 1))
}
bad() {
	echo "❌ $*"
	fail=$((fail + 1))
}
warn() {
	echo "⚠️  $*"
	soft=$((soft + 1))
}

echo "=== Jellyfin validation ==="
echo "URL:   $BASE_URL"
echo "Mount: $MOUNT_POINT"
echo

# 1) Mount readable
if [[ -d $MOUNT_POINT ]] && [[ -n "$(find "$MOUNT_POINT" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null || true)" ]]; then
	ok "CloudMedia mount has entries"
	find "$MOUNT_POINT" -mindepth 1 -maxdepth 1 -print 2>/dev/null | head -20 | sed 's/^/    /'
else
	bad "CloudMedia mount empty or missing — Jellyfin cannot see library files"
fi

# Sample media file existence (non-destructive)
sample_file="$(find "$MOUNT_POINT" \( -name '*.mkv' -o -name '*.mp4' -o -name '*.m4v' \) 2>/dev/null | head -1 || true)"
if [[ -n $sample_file ]]; then
	ok "Sample media file visible: $sample_file"
	# Read first 1KB to confirm fuse-t serves bytes (not just dir listing)
	if dd if="$sample_file" of=/dev/null bs=1024 count=1 2>/dev/null; then
		ok "Sample file readable via fuse-t (1KB probe)"
	else
		bad "Sample file listed but not readable — mount/VFS issue"
	fi
else
	warn "No mkv/mp4 under mount (depth-limited find) — check remote or path names"
fi

# 2) HTTP health / startup
http_code="$(curl -sS -o "$TMP_BODY" -w '%{http_code}' --max-time 5 "$BASE_URL/health" 2>/dev/null || echo '000')"
if [[ $http_code == 200 ]]; then
	ok "GET /health → 200"
elif [[ $http_code == 000 ]]; then
	http_code="$(curl -sS -o "$TMP_BODY" -w '%{http_code}' --max-time 5 "$BASE_URL/" 2>/dev/null || echo '000')"
	if [[ $http_code == 2* || $http_code == 3* ]]; then
		warn "Server responds on / (HTTP $http_code) but /health not ready — finish wizard?"
	else
		bad "Jellyfin not reachable at $BASE_URL (HTTP $http_code)"
	fi
else
	warn "GET /health → HTTP $http_code"
fi

# 3) Public system info (no auth)
if curl -fsS --max-time 5 "$BASE_URL/System/Info/Public" -o "$TMP_INFO" 2>/dev/null; then
	ok "System/Info/Public reachable"
	if command -v python3 >/dev/null 2>&1; then
		set +e
		python3 - "$TMP_INFO" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
print(
    f"    ServerName={d.get('ServerName')} Version={d.get('Version')} "
    f"StartupWizardCompleted={d.get('StartupWizardCompleted')}"
)
sys.exit(3 if d.get("StartupWizardCompleted") is False else 0)
PY
		wiz_ec=$?
		set -e
		if [[ $wiz_ec -eq 3 ]]; then
			warn "Startup wizard not completed — HITL admin setup required"
		fi
	fi
else
	warn "System/Info/Public unavailable (server down or not installed yet)"
fi

# 4) Optional authenticated Items count
if [[ -n $API_KEY ]]; then
	items_json="$(curl -fsS --max-time 15 \
		-H "Authorization: MediaBrowser Token=$API_KEY" \
		"$BASE_URL/Items?Recursive=true&IncludeItemTypes=Movie,Episode&Limit=5" 2>/dev/null || true)"
	if [[ -n $items_json ]] && echo "$items_json" | grep -q '"Items"'; then
		ok "Authenticated Items query returned payload"
		if command -v python3 >/dev/null 2>&1; then
			printf '%s' "$items_json" | python3 -c '
import json, sys
d = json.load(sys.stdin)
names = [i.get("Name") for i in d.get("Items", [])[:3]]
print("    TotalRecordCount=%s sample=%s" % (d.get("TotalRecordCount"), names))
'
		fi
	else
		bad "API key set but Items query failed"
	fi
else
	warn "JELLYFIN_API_KEY unset — skip library item count (set after wizard for full proof)"
fi

echo
echo "Summary: pass=$pass soft=$soft fail=$fail"
if [[ $fail -gt 0 ]]; then
	exit 1
fi
if [[ $soft -gt 0 ]]; then
	exit 2
fi
exit 0
