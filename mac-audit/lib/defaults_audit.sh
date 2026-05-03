#!/usr/bin/env bash
# lib/defaults_audit.sh — check risky macOS system defaults
set -euo pipefail

_check_default() {
	local domain key expected label risky
	domain="$1"
	key="$2"
	expected="$3"
	label="$4"
	risky="$5"
	local actual
	actual=$(defaults read "$domain" "$key" 2>/dev/null || echo "__MISSING__")
	if [[ $actual == "$expected" ]]; then
		if [[ $risky == "bad" ]]; then
			fail "$label  (current: $actual)"
		else
			pass "$label  (current: $actual)"
		fi
	else
		if [[ $risky == "bad" ]]; then
			pass "$label  (not set to risky value)"
		else
			warn "$label  (expected: $expected, got: $actual)"
		fi
	fi
}

_check_firewall() {
	local fw_status fw
	if [[ -x /usr/libexec/ApplicationFirewall/socketfilterfw ]]; then
		fw_status=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null || true)
		case "$fw_status" in
		*"State = 1"* | *enabled*)
			pass "Application Firewall is ON"
			return
			;;
		*"State = 0"* | *disabled*)
			fail "Application Firewall is OFF"
			return
			;;
		esac
	fi

	fw=$(defaults read /Library/Preferences/com.apple.alf globalstate 2>/dev/null || echo "0")
	if [[ $fw -ge 1 ]]; then
		pass "Application Firewall is ON (state: $fw)"
	else fail "Application Firewall is OFF"; fi
}

_check_lock_default() {
	local domain="$1"
	local key="$2"
	local expected="$3"
	local label="$4"
	local actual
	actual=$(defaults read "$domain" "$key" 2>/dev/null || echo "__MISSING__")
	if [[ $actual == "$expected" ]]; then
		pass "$label  (current: $actual)"
	elif [[ $actual == "__MISSING__" ]]; then
		info "$label: legacy preference key not set; verify Lock Screen settings manually on modern macOS"
	else
		warn "$label  (expected: $expected, got: $actual)"
	fi
}

check_defaults() {
	header "macOS Security Defaults"
	local ci_mode="${CI_MODE:-false}"

	info "Gatekeeper status:"
	if spctl --status 2>/dev/null | grep -q "enabled"; then
		pass "Gatekeeper is enabled"
	else
		fail "Gatekeeper is DISABLED"
	fi

	_check_firewall

	_check_lock_default com.apple.screensaver askForPassword 1 \
		"Screen saver requires password"
	_check_lock_default com.apple.screensaver askForPasswordDelay 0 \
		"Password required immediately after lock"

	if [[ $ci_mode != "true" ]]; then
		info "Remote Login (SSH):"
		if systemsetup -getremotelogin 2>/dev/null | grep -q "On"; then
			warn "Remote Login (SSH) is ON — disable if unused"
		else
			pass "Remote Login (SSH) is OFF"
		fi
	else
		info "Remote Login (SSH): skipped in CI (requires interactive sudo)"
	fi

	info "Remote Management (ARD):"
	if pgrep -x ARDAgent &>/dev/null; then
		warn "Apple Remote Desktop agent is running"
	else
		pass "Apple Remote Desktop agent not running"
	fi

	_check_default com.apple.privacy DiagnosticsAutoSubmit 1 \
		"Auto-submit diagnostics to Apple" bad

	info "System Integrity Protection (SIP):"
	if csrutil status 2>/dev/null | grep -q "enabled"; then
		pass "SIP is enabled"
	else
		fail "SIP is DISABLED — high-risk configuration"
	fi

	if [[ $ci_mode != "true" ]]; then
		info "FileVault:"
		if fdesetup status 2>/dev/null | grep -q "On"; then
			pass "FileVault is ON"
		else
			fail "FileVault is OFF — enable in System Settings > Privacy & Security"
		fi
	else
		info "FileVault: skipped in CI (hardware-only check)"
	fi
}
