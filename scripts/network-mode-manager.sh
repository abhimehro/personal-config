#!/bin/bash
#
# Network Mode Manager (Refactored)
# Implements the "Separation Strategy" for Control D and Windscribe.
#
# USAGE: ./scripts/network-mode-manager.sh {controld|windscribe|status} [profile]

set -euo pipefail

trap 'echo -e "
[0;31m?? Operation cancelled by user. Goodbye![0m"; exit 130' SIGINT

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source Core Library
LIB_PATH="$SCRIPT_DIR/lib/network-core.sh"
if [[ -f $LIB_PATH ]]; then
	# shellcheck source=scripts/lib/network-core.sh
	source "$LIB_PATH"
else
	echo "Error: Network core library not found at $LIB_PATH" >&2
	exit 1
fi

# Source optional shared libraries
if [[ -f "$SCRIPT_DIR/lib/network-utils.sh" ]]; then
	# shellcheck source=scripts/lib/network-utils.sh
	source "$SCRIPT_DIR/lib/network-utils.sh"
fi
if [[ -f "$SCRIPT_DIR/lib/dns-utils.sh" ]]; then
	# shellcheck source=scripts/lib/dns-utils.sh
	source "$SCRIPT_DIR/lib/dns-utils.sh"
fi

# --- Configuration ---
DEFAULT_PROFILE="browsing"
IPV6_MANAGER="$SCRIPT_DIR/macos/ipv6-manager.sh"

# --- Logic ---

get_service_dns() {
	local service="$1"
	networksetup -getdnsservers "$service" 2>/dev/null || true
}

system_dns_has_localhost() {
	local wifi_dns lan_dns
	wifi_dns=$(get_service_dns "Wi-Fi")
	lan_dns=$(get_service_dns "USB 10/100/1000 LAN")
	[[ $wifi_dns == *"127.0.0.1"* ]] || [[ $lan_dns == *"127.0.0.1"* ]]
}

# True when the local Control D listener actually answers DNS.
# pgrep alone is insufficient: KeepAlive can leave a zombie process that does
# not bind :53 (empty /etc/controld, crash loop).
ctrld_listener_ready() {
	dig @127.0.0.1 google.com +short +time=1 +tries=1 >/dev/null 2>&1
}

get_active_profile_name() {
	local controld_dir="${CONTROLD_DIR:-/etc/controld}"
	local active_profile_file="$controld_dir/active_profile"
	local config_link="$controld_dir/ctrld.toml"
	local profile_name="Unknown"

	if sudo test -f "$active_profile_file"; then
		profile_name=$(sudo awk -F= '$1 == "PROFILE_NAME" {print $2; exit}' "$active_profile_file" 2>/dev/null || echo "")
	fi

	if [[ -z $profile_name || $profile_name == "Unknown" ]] && sudo test -L "$config_link"; then
		local target extracted_name
		target=$(sudo readlink "$config_link" || echo "")
		extracted_name="${target##*/}"
		extracted_name="${extracted_name#ctrld.}"
		extracted_name="${extracted_name%.toml}"
		extracted_name="${extracted_name%.fallback}"
		profile_name="$extracted_name"
	fi

	case "$profile_name" in
	privacy) echo "Privacy" ;;
	browsing) echo "Browsing" ;;
	gaming) echo "Gaming" ;;
	"" | Unknown) echo "Unknown" ;;
	*) echo "$profile_name" ;;
	esac
}

check_reconcile_needed() {
	local vpn_connected="$1"
	local ctrld_running="$2"
	local ipv6_enabled="$3"
	local profile_mode="${4-}"

	# Intentional doh-ipv4 (DoH + IPv6 off) is healthy whether or not VPN is up.
	# Standalone `controld … doh` and combined Windscribe IPv4-only both use it.
	# Do NOT recommend reconcile solely because VPN is disconnected.
	if [[ $profile_mode == "doh-ipv4" && $ctrld_running == "true" && $ipv6_enabled != "true" ]]; then
		return 1
	fi

	# Standalone Control D expects IPv6 on (doh3-ipv6 / doh-ipv6 without VPN).
	if [[ $vpn_connected != "true" && $ctrld_running == "true" && $ipv6_enabled != "true" ]]; then
		return 0
	fi
	# Combined IPv6-capable VPN mode expects IPv6 on while VPN is connected.
	if [[ $vpn_connected == "true" && $ctrld_running == "true" && $profile_mode == "doh-ipv6" && $ipv6_enabled != "true" ]]; then
		return 0
	fi
	# Combined IPv4-only mode expects IPv6 off — leak if IPv6 is still on.
	if [[ $vpn_connected == "true" && $ctrld_running == "true" && $profile_mode == "doh-ipv4" && $ipv6_enabled == "true" ]]; then
		return 0
	fi
	if [[ $ctrld_running != "true" ]] && system_dns_has_localhost; then
		return 0
	fi
	return 1
}

get_active_profile_mode() {
	local controld_dir="${CONTROLD_DIR:-/etc/controld}"
	local active_profile_file="$controld_dir/active_profile"
	local protocol="" ipv6_policy=""

	if sudo test -f "$active_profile_file"; then
		protocol=$(sudo awk -F= '$1 == "PROTOCOL" {print $2; exit}' "$active_profile_file" 2>/dev/null || echo "")
		ipv6_policy=$(sudo awk -F= '$1 == "IPV6_POLICY" {print $2; exit}' "$active_profile_file" 2>/dev/null || echo "")
		local mode
		mode=$(sudo awk -F= '$1 == "PROFILE_MODE" {print $2; exit}' "$active_profile_file" 2>/dev/null || echo "")
		if [[ -n $mode ]]; then
			echo "$mode"
			return 0
		fi
	fi

	if [[ -z $protocol ]]; then
		protocol="doh3"
	fi
	if [[ -z $ipv6_policy ]]; then
		local wifi_info
		wifi_info=$(networksetup -getinfo "Wi-Fi" 2>/dev/null || echo "")
		if [[ $wifi_info == *"IPv6: Automatic"* ]]; then
			ipv6_policy="enable"
		else
			ipv6_policy="disable"
		fi
	fi
	resolve_network_profile_mode "$protocol" "$ipv6_policy"
}

reconcile_network_state() {
	local profile="${1:-privacy}"
	log "Reconciling network state..."

	if is_vpn_connected; then
		log "VPN is connected; preserving Windscribe-compatible mode."

		# Guard: never lock DNS to localhost unless the listener answers.
		# pgrep alone is insufficient (KeepAlive zombie / empty homedir).
		if ! pgrep -x "ctrld" >/dev/null 2>&1 || ! ctrld_listener_ready; then
			warn "VPN is connected but Control D DNS listener is not healthy. Restarting Control D ($profile) in Windscribe-compatible mode (DoH)."
			# Auto-select IPv6 from tunnel capability (or WINDSCRIBE_IPV6 override).
			if vpn_supports_ipv6; then
				start_controld "$profile" "doh" "enable"
			else
				start_controld "$profile" "doh" "disable"
			fi
			if ! ctrld_listener_ready; then
				# error() exits; print status first so operator sees DNS/VPN state.
				print_status
				error "Control D DNS listener failed while VPN is connected. Leaving DNS unchanged to preserve connectivity. Restart Control D manually or run: ./scripts/network-mode-manager.sh windscribe $profile"
			fi
		fi

		# Align IPv6 + profile-mode metadata with tunnel capability while VPN is up.
		local desired_ipv6="disable"
		local desired_mode="doh-ipv4"
		if vpn_supports_ipv6; then
			desired_ipv6="enable"
			desired_mode="doh-ipv6"
		fi
		set_ipv6 "$desired_ipv6"
		local active_profile_file="${CONTROLD_DIR:-/etc/controld}/active_profile"
		if sudo test -f "$active_profile_file"; then
			sudo sh -c "grep -vE '^(IPV6_POLICY|PROFILE_MODE|PROTOCOL)=' \"$active_profile_file\" > \"$active_profile_file.tmp\" && \
				printf 'PROTOCOL=doh\nIPV6_POLICY=%s\nPROFILE_MODE=%s\n' \"$desired_ipv6\" \"$desired_mode\" >> \"$active_profile_file.tmp\" && \
				mv \"$active_profile_file.tmp\" \"$active_profile_file\" && chmod 600 \"$active_profile_file\"" 2>/dev/null || true
		fi

		# Only pin DNS to localhost after confirming the listener answers.
		if ctrld_listener_ready && ! system_dns_has_localhost; then
			warn "System DNS is not locked to 127.0.0.1 while VPN is connected. Re-applying localhost DNS."
			sudo networksetup -setdnsservers Wi-Fi 127.0.0.1 2>/dev/null || true
			sudo networksetup -setdnsservers "USB 10/100/1000 LAN" 127.0.0.1 2>/dev/null || true
			sudo dscacheutil -flushcache 2>/dev/null || true
			sudo killall -HUP mDNSResponder 2>/dev/null || true
		fi
		print_status
		return 0
	fi

	# Zombie: process or localhost DNS without a working listener.
	if system_dns_has_localhost && ! ctrld_listener_ready; then
		warn "Detected localhost DNS without a working Control D listener. Restoring DNS to DHCP, then restarting standalone Control D ($profile)."
		reset_system_dns
		set_ipv6 "enable"
		start_controld "$profile" "" "enable"
		print_status
		return 0
	fi

	if pgrep -x "ctrld" >/dev/null 2>&1 && system_dns_has_localhost; then
		warn "Detected Control D localhost DNS while VPN is disconnected. Switching back to standalone Control D ($profile)."
		set_ipv6 "enable"
		start_controld "$profile" "" "enable"
		print_status
		return 0
	fi

	if ! pgrep -x "ctrld" >/dev/null 2>&1 && system_dns_has_localhost; then
		warn "Detected localhost DNS but Control D is stopped. Restoring DNS to DHCP."
		reset_system_dns
		set_ipv6 "enable"
		sudo dscacheutil -flushcache 2>/dev/null || true
		sudo killall -HUP mDNSResponder 2>/dev/null || true
		print_status
		return 0
	fi

	local ipv6_state
	ipv6_state=$(networksetup -getinfo "Wi-Fi" 2>/dev/null || echo "")
	if pgrep -x "ctrld" >/dev/null 2>&1 && [[ $ipv6_state != *"IPv6: Automatic"* ]]; then
		local active_mode
		active_mode=$(get_active_profile_mode)
		# Intentional doh-ipv4 (IPv6 off) is healthy without VPN — do not "fix" it.
		# Other modes with IPv6 off and no VPN are stale combined leftovers.
		if [[ $active_mode == "doh-ipv4" ]]; then
			log "Active mode is intentional doh-ipv4 (IPv6 off); no reconciliation needed."
			print_status
			return 0
		fi
		warn "Detected Control D running with IPv6 disabled and no VPN. Re-enabling IPv6 and switching to standalone Control D ($profile)."
		set_ipv6 "enable"
		start_controld "$profile" "" "enable"
		print_status
		return 0
	fi

	log "No reconciliation needed."
	print_status
}

validate_protocol() {
	case "$1" in
	"" | doh | doh3) return 0 ;;
	*) error "Invalid protocol: '$1'. Must be empty (default) or 'doh' or 'doh3'." ;;
	esac
}

ensure_prereqs() {
	ensure_not_root
	check_cmd "ctrld"
	check_cmd "networksetup"

	if [[ ! -x $IPV6_MANAGER ]]; then
		error "IPv6 Manager not found or not executable at $IPV6_MANAGER"
	fi
}

set_ipv6() {
	local state=$1
	log "Setting IPv6 state to: $state..."
	sudo "$IPV6_MANAGER" "$state" >/dev/null
	success "IPv6 state set to $state."
}

stop_controld() {
	log "Stopping Control D service and cleaning up DNS configuration..."
	reset_system_dns
	sudo ctrld service stop 2>/dev/null || true
	sudo pkill -f -- "ctrld" 2>/dev/null || true
	success "Control D stopped and system DNS reset to DHCP."
}

start_controld() {
	local profile_key=$1
	local force_proto=$2
	local ipv6_policy="${3-}" # enable|disable|auto|empty

	case "$profile_key" in
	"privacy") log "Selecting ${E_PRIVACY} PRIVACY profile..." ;;
	"browsing") log "Selecting ${E_BROWSING} BROWSING profile..." ;;
	"gaming") log "Selecting ${E_GAMING} GAMING profile..." ;;
	*) error "Unknown profile '$profile_key'. Available profiles: privacy, browsing, gaming." ;;
	esac

	# Resolve protocol default before IPv6 policy so mode labeling is accurate.
	local effective_proto="${force_proto-}"
	if [[ -z $effective_proto ]]; then
		if command -v get_profile_protocol >/dev/null 2>&1; then
			effective_proto=$(get_profile_protocol "$profile_key")
		else
			effective_proto="doh3"
		fi
	fi

	# Resolve IPv6 policy: explicit > auto(from VPN) > protocol default.
	local effective_ipv6="$ipv6_policy"
	case "$effective_ipv6" in
	enable | disable) ;;
	auto)
		if vpn_supports_ipv6; then
			effective_ipv6="enable"
		else
			effective_ipv6="disable"
		fi
		;;
	"")
		if [[ $effective_proto == "doh" ]]; then
			# DoH without explicit policy: IPv4-only leak prevention by default.
			effective_ipv6="disable"
		else
			effective_ipv6="enable"
		fi
		;;
	*) error "Invalid IPv6 policy '$ipv6_policy'. Use enable, disable, or auto." ;;
	esac

	local profile_mode
	profile_mode=$(resolve_network_profile_mode "$effective_proto" "$effective_ipv6")
	log "Profile mode: $profile_mode (protocol=$effective_proto, ipv6=$effective_ipv6)"

	set_ipv6 "$effective_ipv6"

	log "Starting Control D (profile=$profile_key) via controld-manager..."

	local controld_manager="$SCRIPT_DIR/../controld-system/scripts/controld-manager"
	if [[ ! -x $controld_manager ]]; then
		controld_manager="/usr/local/bin/controld-manager"
	fi
	if [[ ! -x $controld_manager ]]; then
		error "controld-manager script not found in repo or /usr/local/bin. Please run 'scripts/setup-controld.sh' to install it securely."
	fi

	# Call switch with profile and optional protocol override
	if sudo env CTRLD_PRIVACY_PROFILE="${CTRLD_PRIVACY_PROFILE-}" \
		CTRLD_GAMING_PROFILE="${CTRLD_GAMING_PROFILE-}" \
		CTRLD_BROWSING_PROFILE="${CTRLD_BROWSING_PROFILE-}" \
		CTR_PROFILE_PRIVACY_ID="${CTR_PROFILE_PRIVACY_ID:-${CTRLD_PRIVACY_PROFILE-}}" \
		CTR_PROFILE_GAMING_ID="${CTR_PROFILE_GAMING_ID:-${CTRLD_GAMING_PROFILE-}}" \
		CTR_PROFILE_BROWSING_ID="${CTR_PROFILE_BROWSING_ID:-${CTRLD_BROWSING_PROFILE-}}" \
		"$controld_manager" switch "$profile_key" "$force_proto"; then
		# Annotate active_profile with IPv6 policy / mode for reconcile + status.
		local active_profile_file="${CONTROLD_DIR:-/etc/controld}/active_profile"
		if sudo test -f "$active_profile_file"; then
			sudo sh -c "grep -vE '^(IPV6_POLICY|PROFILE_MODE)=' \"$active_profile_file\" > \"$active_profile_file.tmp\" && \
				printf 'IPV6_POLICY=%s\nPROFILE_MODE=%s\n' \"$effective_ipv6\" \"$profile_mode\" >> \"$active_profile_file.tmp\" && \
				mv \"$active_profile_file.tmp\" \"$active_profile_file\" && chmod 600 \"$active_profile_file\"" 2>/dev/null || true
		fi
		success "Control D active (profile: $profile_key, mode: $profile_mode)."
	else
		error "controld-manager failed to switch to profile '$profile_key'."
	fi
}

print_status() {
	echo -e "\n${BOLD}${BLUE}   NETWORK STATUS${NC}"
	echo -e "${BLUE}   --------------${NC}"

	# Control D
	local cd_display
	if pgrep -x "ctrld" >/dev/null 2>&1; then
		local profile_name
		profile_name=$(get_active_profile_name)
		cd_display="${GREEN}* ACTIVE${NC} (${YELLOW}$profile_name${NC})"
	else
		cd_display="${RED}o STOPPED${NC}"
	fi
	printf "   %s  %-13s %b\n" "[CD]" "Control D" "$cd_display"

	# VPN
	local vpn_status="${RED}DISCONNECTED${NC}"
	if is_vpn_connected; then
		vpn_status="${GREEN}CONNECTED${NC}"
	fi
	printf "   %s  %-13s %b\n" "[VPN]" "VPN Tunnel" "$vpn_status"

	# Network Info (Parallel)
	local dns_temp
	dns_temp=$(mktemp -t 'nmm_dns.XXXXXX')
	local info_temp
	info_temp=$(mktemp -t 'nmm_info.XXXXXX')
	(networksetup -getdnsservers "Wi-Fi" 2>/dev/null || echo "Unknown") >"$dns_temp" &
	local pid1=$!
	(networksetup -getinfo "Wi-Fi" 2>/dev/null || echo "") >"$info_temp" &
	local pid2=$!
	wait $pid1 $pid2

	local dns_servers
	dns_servers=$(cat "$dns_temp")
	local wifi_info
	wifi_info=$(cat "$info_temp")
	rm -f "$dns_temp" "$info_temp"

	# DNS Status
	local dns_status
	if [[ $dns_servers == *"There aren't any DNS Servers"* ]]; then
		dns_status="${YELLOW}DHCP (ISP/Router)${NC}"
	elif [[ $dns_servers == *"127.0.0.1"* ]]; then
		dns_status="${GREEN}127.0.0.1 (Localhost)${NC}"
	else
		local cleaner_dns="${dns_servers//$'\n'/, }"
		dns_status="${RED}${cleaner_dns%, }${NC}"
	fi
	printf "   %s  %-13s %b\n" "[DNS]" "System DNS" "$dns_status"

	# IPv6 Status
	local ipv6_enabled="false"
	local ipv6_status="${RED}DISABLED${NC}"
	if [[ $wifi_info == *"IPv6: Automatic"* ]]; then
		ipv6_enabled="true"
		ipv6_status="${GREEN}ENABLED${NC} (Automatic)"
	fi
	printf "   %s  %-13s %b\n" "[v6]" "IPv6 Mode" "$ipv6_status"

	local profile_mode
	profile_mode=$(get_active_profile_mode 2>/dev/null || echo "unknown")
	printf "   %s  %-13s %b\n" "[MODE]" "Profile Mode" "${YELLOW}${profile_mode}${NC}"

	local vpn_connected="false"
	local ctrld_running="false"
	if is_vpn_connected; then
		vpn_connected="true"
	fi
	if pgrep -x "ctrld" >/dev/null 2>&1; then
		ctrld_running="true"
	fi
	if [[ ${NMM_SUPPRESS_RECONCILE_HINT:-0} != "1" ]] && check_reconcile_needed "$vpn_connected" "$ctrld_running" "$ipv6_enabled" "$profile_mode"; then
		local hint_profile
		hint_profile=$(get_active_profile_name)
		case "$hint_profile" in
		Privacy) hint_profile="privacy" ;;
		Browsing) hint_profile="browsing" ;;
		Gaming) hint_profile="gaming" ;;
		*) hint_profile="privacy" ;;
		esac
		printf "   %s  %-13s %b\n" "[!]" "Reconcile" "${YELLOW}Recommended: ./scripts/network-mode-manager.sh reconcile ${hint_profile}${NC}"
	fi
	echo -e "\n"
}

interactive_menu() {
	local active_mode="none"
	if pgrep -x "ctrld" >/dev/null 2>&1; then
		local config_link="/etc/controld/ctrld.toml"
		if sudo test -L "$config_link"; then
			local target
			target=$(sudo readlink "$config_link" || echo "")
			if [[ $target == *"privacy"* ]]; then active_mode="privacy"; fi
			if [[ $target == *"browsing"* ]]; then active_mode="browsing"; fi
			if [[ $target == *"gaming"* ]]; then active_mode="gaming"; fi
		fi
	elif is_vpn_connected; then
		active_mode="vpn"
	fi

	local m_priv="  " m_brow="  " m_game="  " m_vpn="  "
	case "$active_mode" in
	privacy) m_priv="${GREEN}[on]${NC}" ;;
	browsing) m_brow="${GREEN}[on]${NC}" ;;
	gaming) m_game="${GREEN}[on]${NC}" ;;
	vpn) m_vpn="${GREEN}[on]${NC}" ;;
	esac

	echo -e "\n${BOLD}${BLUE}Network Mode Manager${NC}"
	echo -e "   1) ${E_PRIVACY} Control D (Privacy)          $m_priv"
	echo -e "   2) ${E_BROWSING} Control D (Browsing)         $m_brow ${YELLOW}[Default]${NC}"
	echo -e "   3) ${E_GAMING} Control D (Gaming)           $m_game"
	echo -e "   4) ${E_VPN} Windscribe (VPN)             $m_vpn"
	echo -e "   5) ${E_INFO} Show Status"
	echo -e "   0) Exit"

	while true; do
		echo -ne "\n${BOLD}Select option [0-5] (Enter for Default): ${NC}"
		read -r choice
		choice="${choice:-2}"

		case "$choice" in
		1) main "controld" "privacy" ;;
		2) main "controld" "browsing" ;;
		3) main "controld" "gaming" ;;
		4) main "windscribe" ;;
		5) main "status" ;;
		0) exit 0 ;;
		*)
			echo -e "${RED}Invalid option, please try again.${NC}"
			continue
			;;
		esac
		break
	done
}

main() {
	local mode="${1-}"
	local profile="${2:-$DEFAULT_PROFILE}"

	if [[ $mode == "-h" || $mode == "--help" || $mode == "help" ]]; then
		echo "Usage: $0 {controld|windscribe|status|reconcile} [profile] [protocol]"
		echo ""
		echo "Profile modes:"
		echo "  doh-ipv4   DoH + IPv6 disabled  (Windscribe IPv4-only / static IP)"
		echo "  doh3-ipv6  DoH3 + IPv6 enabled  (standalone Control D; default)"
		echo "  doh-ipv6   DoH + IPv6 enabled   (Windscribe IPv6-capable WireGuard)"
		echo ""
		echo "Examples:"
		echo "  $0 controld browsing            # DoH3 + IPv6 on"
		echo "  $0 controld privacy doh         # DoH + IPv6 off (leak prevention)"
		echo "  $0 windscribe privacy           # Combined; auto IPv6 from tunnel"
		echo "  WINDSCRIBE_IPV6=1 $0 windscribe privacy   # Force DoH + IPv6 on (bash/zsh)"
		echo "  WINDSCRIBE_IPV6=0 $0 windscribe privacy   # Force DoH + IPv6 off (bash/zsh)"
		echo "  env WINDSCRIBE_IPV6=1 $0 windscribe privacy  # fish"
		echo "  env WINDSCRIBE_IPV6=0 $0 windscribe privacy  # fish"
		exit 0
	fi

	if [[ -z $mode ]]; then
		interactive_menu
		exit 0
	fi

	ensure_prereqs
	load_network_env

	case "$mode" in
	windscribe)
		local profile="${2-}"
		if [[ -n $profile ]]; then
			log "Switching to WINDSCRIBE + CONTROL D ($profile) MODE..."
			# Auto IPv6: enable for IPv6-capable tunnels, disable for IPv4-only/static.
			# Before connect, tunnel may not exist yet -- honor WINDSCRIBE_IPV6 or
			# default to disable (safe leak-prevention), then reconcile after connect.
			local ipv6_policy="auto"
			if [[ -z ${WINDSCRIBE_IPV6-} ]] && ! is_vpn_connected; then
				ipv6_policy="disable"
				log "VPN not yet connected; defaulting to DoH + IPv6 disabled (leak prevention). Re-run reconcile or windscribe-connect after connect to enable IPv6 if the server supports it."
			fi
			start_controld "$profile" "doh" "$ipv6_policy"
		else
			log "Switching to STANDALONE WINDSCRIBE (VPN) MODE..."
			stop_controld
			set_ipv6 "disable"
		fi
		(NMM_SUPPRESS_RECONCILE_HINT=1 print_status)
		;;
	controld)
		local proto="${3-}"
		validate_protocol "$proto"
		log "Switching to CONTROL D (DNS) MODE..."
		# Standalone Control D: DoH3 defaults to IPv6 on; explicit DoH keeps
		# IPv6 off for leak-prevention / IPv4-only compatibility unless the
		# caller sets CONTROLD_IPV6=enable (new doh-ipv6 mode without VPN).
		local ipv6_policy="enable"
		if [[ $proto == "doh" ]]; then
			case "${CONTROLD_IPV6-}" in
			enable | 1 | true | TRUE | on | ON) ipv6_policy="enable" ;;
			*) ipv6_policy="disable" ;;
			esac
		fi
		start_controld "$profile" "$proto" "$ipv6_policy"
		print_status
		;;
	status)
		print_status
		;;
	reconcile)
		reconcile_network_state "$profile"
		;;
	*)
		error "Invalid mode '$mode'"
		;;
	esac
}

if [[ ${BASH_SOURCE[0]} == "${0}" ]]; then
	main "$@"
fi
