#!/usr/bin/env bash
# Verify no obvious committed credentials (ABHI-964 / ABHI-918 acceptance helper).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

failures=0

echo "=== ABHI-964: Repository credential hygiene ==="

# Gitignored secret-bearing files must stay ignored
for pattern in GH_TOKEN.env .env; do
	if ! grep -qxF "$pattern" .gitignore 2>/dev/null; then
		echo "✗ .gitignore missing: $pattern"
		failures=$((failures + 1))
	else
		echo "✓ .gitignore lists $pattern"
	fi
done

# Tracked files: block common secret shapes (allow placeholders)
scan_paths=(
	.
)
exclude_dirs=(
	--exclude-dir=.git
	--exclude-dir=.trunk
	--exclude-dir=node_modules
	--exclude-dir=archive
)

if git grep -nE 'ghp_[A-Za-z0-9]{20,}' "${scan_paths[@]}" "${exclude_dirs[@]}" 2>/dev/null; then
	echo "✗ Found GitHub PAT-like pattern (ghp_) in tracked content"
	failures=$((failures + 1))
else
	echo "✓ No ghp_ PAT patterns in tracked files"
fi

if git grep -nE 'github_pat_[A-Za-z0-9_]{20,}' "${scan_paths[@]}" "${exclude_dirs[@]}" 2>/dev/null; then
	echo "✗ Found github_pat_ token pattern in tracked content"
	failures=$((failures + 1))
else
	echo "✓ No github_pat_ patterns in tracked files"
fi

# Legacy hardcoded WebDAV curl examples (literal password in quotes)
if git grep -nE 'curl -u "infuse:[^$"\{]+"' media-streaming "${exclude_dirs[@]}" 2>/dev/null |
	grep -v "\${MEDIA_WEBDAV_PASS}" |
	grep -v "generated-secret" |
	grep -v '<set in'; then
	echo "✗ Found hardcoded curl -u infuse:password examples"
	failures=$((failures + 1))
else
	echo "✓ No hardcoded infuse:password curl examples in media-streaming"
fi

# Placeholder-based docs are expected
if grep -rq 'MEDIA_WEBDAV_PASS' media-streaming 2>/dev/null; then
	echo "✓ MEDIA_WEBDAV_PASS placeholders present in media-streaming docs/scripts"
else
	echo "⚠️  No MEDIA_WEBDAV_PASS references found (unexpected)"
fi

echo ""
if [[ $failures -gt 0 ]]; then
	echo "=== FAILED: $failures credential hygiene check(s) ==="
	exit 1
fi

echo "=== All credential hygiene checks passed ==="
echo "NOTE: Rotate live PAT/WebDAV per ABHI-918 in GitHub Settings and 1Password."
exit 0
