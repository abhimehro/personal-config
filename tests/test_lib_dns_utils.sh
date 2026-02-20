#!/bin/bash
#
# Unit tests for scripts/lib/dns-utils.sh
# Tests dns_lookup_cached, dns_cache_clear, dns_cache_destroy, and dns_health_check

set -euo pipefail

# Setup
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-dns-utils')
MOCK_BIN="$TEST_DIR/bin"
mkdir -p "$MOCK_BIN"
trap 'rm -rf "$TEST_DIR"' EXIT

# Use an isolated cache directory for tests
export DNS_CACHE_DIR="$TEST_DIR/dns_cache"

# --- Mock dig ---
# Returns a predictable IP so we can verify caching behaviour
cat > "$MOCK_BIN/dig" << 'EOF'
#!/bin/bash
# Emit a fake answer for any host that looks like "google.com" or "p.controld.com"
case "$*" in
    *"google.com"*|*"p.controld.com"*)
        echo "1.2.3.4"
        exit 0
        ;;
    *"fail.example.com"*)
        # Simulate NXDOMAIN – no output, non-zero exit
        exit 1
        ;;
    *)
        echo "5.6.7.8"
        exit 0
        ;;
esac
EOF
chmod +x "$MOCK_BIN/dig"
export PATH="$MOCK_BIN:$PATH"

# Source the library under test
# shellcheck source=scripts/lib/dns-utils.sh
source "$REPO_ROOT/scripts/lib/dns-utils.sh"

PASS=0
FAIL=0

check() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name"
        FAIL=$((FAIL + 1))
    fi
}

check_output() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name (expected='$expected', got='$actual')"
        FAIL=$((FAIL + 1))
    fi
}

check_false() {
    local name="$1"; shift
    if ! "$@" >/dev/null 2>&1; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Testing scripts/lib/dns-utils.sh ==="

# --- dns_cache_init ---
echo ""
echo "-- dns_cache_init --"
dns_cache_init
check "dns_cache_init creates cache directory" test -d "$DNS_CACHE_DIR"
check "dns_cache_init creates a real directory (not symlink)" test ! -L "$DNS_CACHE_DIR"

# --- dns_lookup_cached: first call (cache miss) ---
echo ""
echo "-- dns_lookup_cached (cache miss) --"
RESULT=$(dns_lookup_cached "google.com" 60)
check_output "cache miss returns IP from dig" "1.2.3.4" "$RESULT"
check "cache miss creates cache file" test -f "$DNS_CACHE_DIR/google.com.cache"
check "cache file contains two lines (timestamp + result)" bash -c \
    'test "$(wc -l < '"\"$DNS_CACHE_DIR/google.com.cache\""')" -eq 2'

# --- dns_lookup_cached: second call (cache hit) ---
echo ""
echo "-- dns_lookup_cached (cache hit) --"
# Replace mock dig with one that fails so we know the result came from cache
cat > "$MOCK_BIN/dig" << 'EOF'
#!/bin/bash
echo "UNEXPECTED DIG CALL" >&2
exit 1
EOF
CACHED=$(dns_lookup_cached "google.com" 60)
check_output "cache hit returns cached IP (no dig call)" "1.2.3.4" "$CACHED"

# Restore the working mock dig for further tests
cat > "$MOCK_BIN/dig" << 'EOF'
#!/bin/bash
case "$*" in
    *"google.com"*|*"p.controld.com"*)
        echo "1.2.3.4"
        exit 0
        ;;
    *"fail.example.com"*)
        exit 1
        ;;
    *)
        echo "5.6.7.8"
        exit 0
        ;;
esac
EOF

# --- dns_lookup_cached: hostname sanitisation ---
echo ""
echo "-- dns_lookup_cached hostname sanitisation --"
# A hostname with embedded shell-special characters should return empty (sanitised to nothing)
BAD=$(dns_lookup_cached "" 60 || true)
check "lookup of empty hostname returns empty" test -z "$BAD"

# --- dns_cache_clear ---
echo ""
echo "-- dns_cache_clear --"
dns_lookup_cached "other.example" 60 >/dev/null || true
dns_cache_clear
check "dns_cache_clear removes .cache files" bash -c 'ls '"$DNS_CACHE_DIR"'/*.cache 2>/dev/null | wc -l | grep -qx "0"'

# --- dns_cache_destroy ---
echo ""
echo "-- dns_cache_destroy --"
dns_cache_destroy
check_false "dns_cache_destroy removes cache directory" test -d "$DNS_CACHE_DIR"

# --- dns_health_check ---
echo ""
echo "-- dns_health_check --"
# Re-init cache for health check tests
dns_cache_init

check "dns_health_check with resolver returns true for valid host" \
    dns_health_check "127.0.0.1" "google.com"

check "dns_health_check without resolver uses system DNS" \
    dns_health_check "" "google.com"

check_false "dns_health_check returns false for failing host" \
    dns_health_check "" "fail.example.com"

# --- Source guard ---
echo ""
echo "-- source guard --"
source "$REPO_ROOT/scripts/lib/dns-utils.sh"
check "source guard is set" test "$_DNS_UTILS_SH_" = "true"

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
