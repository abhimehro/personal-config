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
		[[ $risky == "bad" ]] && fail "$label  (current: $actual)" ||
			pass "$label  (current: $actual)"
	else
		[[ $risky == "bad" ]] && pass "$label  (not set to risky value)" ||
			warn "$label  (expected: $expected, got: $actual)"
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
	spctl --status 2>/dev/null | grep -q "enabled" &&
		pass "Gatekeeper is enabled" ||
		fail "Gatekeeper is DISABLED"

	_check_firewall

	_check_lock_default com.apple.screensaver askForPassword 1 \
		"Screen saver requires password"
	_check_lock_default com.apple.screensaver askForPasswordDelay 0 \
		"Password required immediately after lock"

	if [[ $ci_mode != "true" ]]; then
		info "Remote Login (SSH):"
		systemsetup -getremotelogin 2>/dev/null | grep -q "On" &&
			warn "Remote Login (SSH) is ON — disable if unused" ||
			pass "Remote Login (SSH) is OFF"
	else
		info "Remote Login (SSH): skipped in CI (requires interactive sudo)"
	fi

	info "Remote Management (ARD):"
	pgrep -x ARDAgent &>/dev/null &&
		warn "Apple Remote Desktop agent is running" ||
		pass "Apple Remote Desktop agent not running"

	_check_default com.apple.privacy DiagnosticsAutoSubmit 1 \
		"Auto-submit diagnostics to Apple" bad

	info "System Integrity Protection (SIP):"
	csrutil status 2>/dev/null | grep -q "enabled" &&
		pass "SIP is enabled" ||
		fail "SIP is DISABLED — high-risk configuration"

	if [[ $ci_mode != "true" ]]; then
		info "FileVault:"
		fdesetup status 2>/dev/null | grep -q "On" &&
			pass "FileVault is ON" ||
			fail "FileVault is OFF — enable in System Settings > Privacy & Security"
	else
		info "FileVault: skipped in CI (hardware-only check)"
	fi
}
