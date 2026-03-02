#!/bin/bash
#
# Control D Service Management Library
# Service lifecycle management, directory setup, and status reporting.
#
# Usage: source "scripts/lib/controld-service.sh"

# Source Guard
if [[ "${_CONTROLD_SERVICE_SH_:-}" == "true" ]]; then
    return
fi
_CONTROLD_SERVICE_SH_="true"

# Setup necessary directory structure
setup_directories() {
    local controld_dir="$1"
    local profiles_dir="$2"
    local backup_dir="$3"
    local log_file="$4"

    # Pre-flight hardening for log file to prevent symlink-based log hijacking
    if [[ -L "$log_file" ]]; then
        echo "Security Alert: $log_file is a symlink! Aborting to prevent log hijack." >&2
        return 1
    fi
    if [[ -e "$log_file" && ! -f "$log_file" ]]; then
        echo "Security Alert: $log_file is not a regular file! Aborting." >&2
        return 1
    fi

    # Sentinel: Verify all critical paths are not symlinks before creation
    _check_not_symlink() {
        local path="$1" label="${2:-$1}"
        if command -v assert_not_symlink >/dev/null 2>&1; then
            assert_not_symlink "$path" "$label" || { return 1; }
        elif [[ -L "$path" ]]; then
            return 1
        fi
        return 0
    }

    _check_not_symlink "$controld_dir" "CONTROLD_DIR" || return 1
    _check_not_symlink "$profiles_dir" "PROFILES_DIR" || return 1
    _check_not_symlink "$backup_dir" "BACKUP_DIR" || return 1

    # Sentinel: Securely create directories
    if command -v secure_mkdir >/dev/null 2>&1; then
        secure_mkdir "$controld_dir" 700 || return 1
        secure_mkdir "$profiles_dir" 700 || return 1
        secure_mkdir "$backup_dir" 700 || return 1
    else
        [[ -e "$controld_dir" && ! -d "$controld_dir" ]] && return 1
        install -d -m 700 "$controld_dir" "$profiles_dir" "$backup_dir"
    fi

    # Sentinel: Post-creation verification
    if [[ -L "$controld_dir" ]] || [[ -L "$profiles_dir" ]] || [[ -L "$backup_dir" ]]; then
        return 1
    fi
    if [[ ! -d "$controld_dir" ]] || [[ ! -d "$profiles_dir" ]] || [[ ! -d "$backup_dir" ]]; then
        return 1
    fi

    # Sentinel: Securely create log file
    if [[ -L "$log_file" ]]; then
        rm -f "$log_file"
    fi
    if [[ ! -e "$log_file" ]]; then
        (umask 077 && touch "$log_file") 2>/dev/null || true
    fi

    if [[ -L "$log_file" ]]; then
        : # Skip permission change
    elif [[ -f "$log_file" ]]; then
        chmod 600 "$log_file" 2>/dev/null || true
    fi

    return 0
}

# Wait for process to stop
_wait_for_process_stop() {
    if command -v wait_for_process_stop >/dev/null 2>&1; then
        wait_for_process_stop "$@"
        return
    fi
    local process_name="$1"
    local max_retries="${2:-20}"
    local retry=0
    while pgrep -x "$process_name" >/dev/null 2>&1 && [[ $retry -lt $max_retries ]]; do
        sleep 0.1
        retry=$((retry + 1))
    done
}

# Safely stop the Control D service
safe_stop() {
    local backup_dir="$1"

    ctrld stop 2>/dev/null || true
    pkill -x ctrld 2>/dev/null || true

    _wait_for_process_stop "ctrld" 20

    if pgrep -x "ctrld" >/dev/null; then
        pkill -9 -x ctrld 2>/dev/null || true
        sleep 0.1
    fi

    if command -v restore_network_settings >/dev/null 2>&1; then
        restore_network_settings "$backup_dir"
    fi

    return 0
}

# Stop the current service, link config, and restart
restart_with_config() {
    local config_file="$1"
    local controld_dir="$2"
    local protocol="$3"
    local listener_ip="$4"

    ctrld stop 2>/dev/null || true
    pkill -f ctrld 2>/dev/null || true

    _wait_for_process_stop "ctrld" 30

    # Create symlink to active configuration
    ln -sf "$config_file" "$controld_dir/ctrld.toml"

    # Start service
    if [[ "$protocol" == "doh3" ]]; then
        ctrld start --config="$controld_dir/ctrld.toml" --skip_self_checks
    else
        ctrld start --config="$controld_dir/ctrld.toml" --skip_self_checks
    fi

    # Wait for service to initialize
    local retry=0
    while ! dig @"$listener_ip" google.com +short +time=1 >/dev/null 2>&1 && [[ $retry -lt 30 ]]; do
        sleep 0.1
        ((retry++))
    done

    # Configure system DNS
    networksetup -setdnsservers Wi-Fi "$listener_ip"

    # Validate DNS configuration
    sleep 0.2
    local configured_dns
    configured_dns=$(networksetup -getdnsservers Wi-Fi 2>/dev/null || echo "")
    if ! echo "$configured_dns" | grep -q "$listener_ip"; then
      sleep 0.5
      networksetup -setdnsservers Wi-Fi "$listener_ip"
    fi

    # Flush DNS cache
    dscacheutil -flushcache 2>/dev/null || true
    sudo killall -HUP mDNSResponder 2>/dev/null || true

    return 0
}

# Emergency recovery
emergency_recovery() {
    local backup_dir="$1"
    local controld_dir="$2"

    pkill -9 -f ctrld 2>/dev/null || true
    rm -f "$controld_dir/ctrld.toml"

    if command -v restore_network_settings >/dev/null 2>&1; then
        restore_network_settings "$backup_dir"
    fi

    sudo dscacheutil -flushcache 2>/dev/null || true
    sudo killall -HUP mDNSResponder 2>/dev/null || true

    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Show status of Control D manager
show_status() {
    local controld_dir="$1"

    echo "=== Control D Profile Manager Status ==="
    echo

    if pgrep -f ctrld >/dev/null; then
        echo "Service Status: ✅ Running"

        if [[ -L "$controld_dir/ctrld.toml" ]]; then
            local current_config
            current_config=$(readlink "$controld_dir/ctrld.toml")
            local extracted_name="${current_config##*/}"
            local profile_name="${extracted_name#ctrld.}"
            profile_name="${profile_name%.toml}"
            local protocol
            protocol=$(grep "type = " "$current_config" 2>/dev/null | sed "s/.*type = '\(.*\)'.*/\1/" || echo "unknown")
            local profile_id="unknown"
            if command -v get_profile_id >/dev/null 2>&1; then
                profile_id=$(get_profile_id "$profile_name")
                if command -v redact_profile_id >/dev/null 2>&1; then
                    profile_id=$(redact_profile_id "$profile_id")
                fi
            fi

            echo "Active Profile: $profile_name"
            echo "Profile ID: $profile_id"
            echo "Protocol: $protocol"
        else
            echo "Active Profile: Unknown (direct configuration)"
        fi

        local dns_servers
        dns_servers=$(networksetup -getdnsservers Wi-Fi 2>/dev/null || echo "Unknown")
        echo "System DNS: $dns_servers"

        if command -v test_current_connection >/dev/null 2>&1; then
            if test_current_connection "$controld_dir" >/dev/null 2>&1; then
                echo "Connection: ✅ Working"
            else
                echo "Connection: ❌ Issues detected"
            fi
        else
             echo "Connection: ⚠️ Cannot verify (missing functions)"
        fi
    else
        echo "Service Status: ❌ Stopped"
    fi

    echo
    echo "Available Profiles:"
    if command -v get_all_profiles >/dev/null 2>&1; then
        for profile in $(get_all_profiles); do
            local default_protocol="unknown"
            local profile_id="unknown"
            if command -v get_profile_protocol >/dev/null 2>&1; then
                default_protocol=$(get_profile_protocol "$profile")
            fi
            if command -v get_profile_id >/dev/null 2>&1; then
                profile_id=$(get_profile_id "$profile")
                if command -v redact_profile_id >/dev/null 2>&1; then
                    profile_id=$(redact_profile_id "$profile_id")
                fi
            fi
            echo "  - $profile ($profile_id) - Default: $default_protocol"
        done
    fi

    echo
    echo "Protocols:"
    echo "  - doh3: DNS-over-HTTPS/3 (QUIC) - Faster, more secure"
    echo "  - doh:  DNS-over-HTTPS (TCP) - Fallback for compatibility"
}

# Self-execution guard for testing
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Return 0 when executed directly
    return 0 2>/dev/null
fi
