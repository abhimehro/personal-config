

**AI summary**  
The document provides the finalized Phase 1 Implementation Plan for a "Separation Strategy" to manage two network modes: Control D (DNS Mode) and Windscribe (VPN Mode), replacing older, conflicting scripts.

Key components of the plan include:

1. The New Manager Script (scripts/network-mode-manager.sh):  
   * Replaces old managers (controld-manager, windscribe-controld).  
   * Implements the "Least Privilege" model (runs as a normal user, uses sudo only when necessary).  
   * Reuses an existing ipv6-manager.sh script for centralized IPv6 management.  
   * Supports three commands: controld \[profile\], windscribe, and status.  
   * When in controld mode, it enables IPv6, stops any old Control D processes, starts ctrld using a cloud profile UID (e.g., "gaming"), and sets the Wi-Fi DNS to the local listener IP (default 127.0.0.1).  
   * When in windscribe mode, it stops Control D, disables IPv6, and resets the Wi-Fi DNS to "Empty" (DHCP), preparing the system for the VPN.  
2. Critical Implementation Details:  
   * Listener IP (LISTENER\_IP): Recommended to be 127.0.0.1 for security and to prevent conflicts with the VPN, as the usage is standalone.  
   * DoH3 Enforcement: Handled via the Control D cloud dashboard; the script uses the \--cd \<UID\> flag, which respects the cloud configuration.  
3. Documentation Update: The controld-system/README.md must be updated with a new "Network Mode Management" section detailing the usage of scripts/network-mode-manager.sh, noting that it replaces the old scripts.  
4. Analysis of Improvements: Highlights increased security ("No 'Root' Risk"), better maintainability ("Code Reuse"), and robustness ("Fail-Safe DNS") by explicitly setting the DNS after service start.

The comprehensive analysis of your recent Warp IDE session is not only accurate but provides an exceptional foundation for the next phase of your network management system. It correctly pinpoints the core problem: the `controld-manager` script was fundamentally flawed because it attempted to manage state (DNS/IPv6 settings) in direct conflict with the atomic, state-driven design of the `ctrld` utility.

The proposed **"Separation Strategy"** is the definitive architectural fix. By dedicating `ctrld` to its singular purpose—running the DNS resolver defined by the cloud configuration—and managing network state (IPv6, DNS pointers) through a separate, dedicated shell script, you perfectly align your system with the **"Infrastructure as Code" (IaC)** philosophy already established in your `WARP.md`. This move dramatically simplifies state management, positioning the Control D cloud dashboard as the undisputed source of truth for DNS filtering.-----Phase 1 Implementation Plan: The Network Mode Manager

This section details the finalized implementation plan for the new network management system, incorporating critical security and robustness improvements discussed during the review.1. The New Manager Script: `scripts/network-mode-manager.sh`

This single script replaces all your previous, fractured managers (`controld-manager`, `windscribe-controld`, etc.). It strictly adheres to the "Least Privilege" security model, running as your normal user and escalating privileges via `sudo` only for necessary system changes (DNS, service control). Furthermore, it promotes code modularity by reusing the logic in your existing `ipv6-manager.sh`.

**(Ensure execution rights are granted: `chmod +x scripts/network-mode-manager.sh`)**

\#\!/bin/bash

\#

\# Network Mode Manager

\# Implements the "Separation Strategy" for Control D and Windscribe.

\# This script manages the state of the network interface (Wi-Fi) to switch

\# between a secure DNS-managed state (Control D) and a clean state

\# ready for VPN use (Windscribe).

\#

\# MODES:

\#   controld   \-\> Enables Control D (DoH3), Ensures IPv6 is Enabled.

\#   windscribe \-\> Disables Control D, Disables IPv6 (Leak Protection), Resets DNS for VPN readiness.

\#   status     \-\> Shows current network state.

\#

\# USAGE: ./scripts/network-mode-manager.sh {controld|windscribe|status} \[profile\]

set \-euo pipefail

\# \--- Configuration \---

\# Map profiles to Control D Resolver UIDs (Retrieved from your Dashboard)

declare \-A PROFILES=(

  \["privacy"\]="6m971e9jaf"

  \["browsing"\]="rcnz7qgvwg"

  \["gaming"\]="1xfy57w34t7"

)

DEFAULT\_PROFILE="browsing"

\# IP where ctrld listens. Standard is 127.0.0.1 (Localhost).

\# CRITICAL: This MUST be the IP the network setup points to.

LISTENER\_IP="127.0.0.1"

\# Path to your existing macOS-specific IPv6 manager

IPV6\_MANAGER="./scripts/macos/ipv6-manager.sh"

\# Colors for improved readability

RED='\\033\[0;31m'

GREEN='\\033\[0;32m'

BLUE='\\033\[0;34m'

NC='\\033\[0m'

\# \--- Helpers \---

log()      { echo \-e "${BLUE}\[INFO\]${NC} $\*"; }

success()  { echo \-e "${GREEN}\[OK\]${NC} $\*"; }

error()    { echo \-e "${RED}\[ERR\]${NC} $\*" \>&2; exit 1; }

ensure\_prereqs() {

    \# Security Check: Prevent root execution to uphold the Least Privilege principle.

    if \[\[ $EUID \-eq 0 \]\]; then

        error "Please run as your normal user (not root). The script will ask for sudo when needed."

    fi

    \# Dependency checks

    command \-v ctrld \>/dev/null 2\>&1 || error "ctrld utility not found. Is it in your PATH?"

    command \-v networksetup \>/dev/null 2\>&1 || error "networksetup not found. Are you on macOS?"

    

    \# Check for the required modular script

    if \[\[ \! \-x "$IPV6\_MANAGER" \]\]; then

        error "IPv6 Manager not found or not executable at $IPV6\_MANAGER"

    fi

}

\# \--- Core Logic \---

set\_ipv6() {

    local state=$1 \# "enable" or "disable"

    log "Setting IPv6 state to: $state..."

    \# Execute the dedicated IPv6 script using sudo

    sudo "$IPV6\_MANAGER" "$state" \>/dev/null

    success "IPv6 state set."

}

stop\_controld() {

    log "Stopping Control D service and cleaning up DNS configuration..."

    \# Attempt a graceful service stop first

    sudo ctrld service stop 2\>/dev/null || true

    \# Aggressively kill any lingering processes to ensure a clean state

    sudo pkill \-f "ctrld" 2\>/dev/null || true

    

    \# Reset System DNS to 'Empty' (DHCP/Router-managed)

    \# This is critical for VPNs, as 'Empty' signals macOS to use the DNS provided by the current network (e.g., the VPN tunnel)

    sudo networksetup \-setdnsservers "Wi-Fi" "Empty" 2\>/dev/null || true

    success "Control D stopped. System DNS reset."

}

start\_controld() {

    local profile\_key=$1

    local uid="${PROFILES\[$profile\_key\]:-}"

    \[\[ \-z "$uid" \]\] && error "Unknown profile '$profile\_key'. Available profiles: ${\!PROFILES\[@\]}"

    log "Starting Control D (Profile: $profile\_key | UID: $uid)..."

    \# Start ctrld, forcing it to pull the latest configuration from the cloud (--cd).

    \# \--listener-ip is explicitly set to 127.0.0.1 for security.

    \# \--iface="auto" allows ctrld to dynamically bind to the correct WAN interface.

    sudo ctrld service start \--cd "$uid" \--listener-ip "$LISTENER\_IP" \--iface="auto" 2\>/dev/null

    \# Wait for the daemon to fully initialize and bind to the port.

    sleep 3

    \# Explicitly enforce DNS setting (Robustness check)

    \# This step is the manual component of the "Separation Strategy"

    sudo networksetup \-setdnsservers "Wi-Fi" "$LISTENER\_IP"

    success "Control D active on $LISTENER\_IP ($profile\_key). System DNS configured."

}

print\_status() {

    echo \-e "\\

${BLUE}=== Network Status \===${NC}"

      

    echo \-n "Control D Process: "

    if pgrep \-x "ctrld" \>/dev/null; then

        echo \-e "${GREEN}RUNNING${NC}"

        \# Attempt to get the running UID for more details

        RUNNING\_UID=$(sudo ctrld status | grep 'Resolver ID' | awk '{print $NF}' 2\>/dev/null || echo "N/A")

        echo \-e "  Resolver ID: ${GREEN}$RUNNING\_UID${NC}"

    else

        echo \-e "${RED}STOPPED${NC}"

    fi

    echo \-n "System DNS (Wi-Fi): "

    networksetup \-getdnsservers "Wi-Fi"

    echo \-e "" \# Newline for clean output

    echo \-n "IPv6 Status: "

    \# Detailed IPv6 status via networksetup

    if networksetup \-getinfo "Wi-Fi" | grep \-q "IPv6: Automatic"; then

        echo \-e "${GREEN}ENABLED (Automatic)${NC}"

    else

        echo \-e "${RED}DISABLED/Manual${NC}"

    fi

}

\# \--- Main Dispatcher \---

main() {

    ensure\_prereqs


    local mode="${1:-}"

    local profile="${2:-$DEFAULT\_PROFILE}" \# Default to 'browsing' if no profile is specified

    case "$mode" in

        windscribe)

            echo \-e "${BLUE}\>\>\> Switching to WINDSCRIBE (VPN) MODE${NC}"

            stop\_controld       \# 1\. Clean up DNS and stop resolver

            set\_ipv6 "disable"  \# 2\. Disable IPv6 to prevent leaks (VPN requirement)

            success "System is now configured for VPN readiness."

            print\_status

            ;;


        controld)

            echo \-e "${BLUE}\>\>\> Switching to CONTROL D (DNS) MODE${NC}"

            set\_ipv6 "enable"   \# 1\. Enable IPv6 for full connectivity

            stop\_controld       \# 2\. Clean slate for a reliable start

            start\_controld "$profile" \# 3\. Start resolver and set system DNS

            success "System is now protected by Control D."

            print\_status

            ;;


        status)

            print\_status

            ;;


        \*)

            echo "Usage: $0 {controld|windscribe|status} \[profile\_name\]"

            echo "Available Profiles: ${\!PROFILES\[@\]}"

            exit 1

            ;;

    esac

}


main "$@"

2\. Critical Implementation Details & Refinements

The following details ensure the script operates reliably and securely within the macOS and `ctrld` environment:A. The Listener IP (`LISTENER_IP`)

| Setting | Recommendation | Rationale |
| ----- | ----- | ----- |
| **Value** | `127.0.0.1` (Localhost) | This is the most secure and reliable setting for a standalone client. Binding only to the local loopback interface ensures that the DNS service is not exposed to the local area network (LAN), preventing other devices from using your Mac as a resolver. Crucially, it minimizes the chance of port conflicts with the Windscribe VPN interface, which often tries to intercept traffic on `0.0.0.0`. |
| **Action** | The script is defaulted to `127.0.0.1`. If `ctrld` unexpectedly fails to start or resolve, the only alternative is to test `0.0.0.0` (All Interfaces), but this is not recommended unless absolutely necessary. |  |

B. DoH3 Enforcement and Cloud State

The design leverages the intelligence of the `ctrld` binary:

* When you use the `--cd <UID>` flag, the binary fetches and applies the **entire configuration** defined in the Control D Dashboard.  
* **Action:** Ensure your profiles (especially "Gaming") are set to **DoH3** or **Auto** in your [Control D Dashboard](https://www.google.com/search?q=https://controld.com/control-panel/profiles). The script does *not* need the `--proto` CLI flag, as the cloud configuration supersedes manual settings, keeping your script simple and declarative.

C. Modular IPv6 Management

* The script uses the variable `IPV6_MANAGER="./scripts/macos/ipv6-manager.sh"`.  
* **Action:** Verify that this path is correct relative to the location where you execute `network-mode-manager.sh`. Maintaining this external script ensures that the IPv6 logic remains consistent and centralized.

3\. Documentation Updates (Phase 1 Wrap-up)

To prevent confusion and ensure future maintainers (including yourself) use the correct flow, the `controld-system/README.md` must be updated to deprecate the old scripts.

**Add the following section to your `controld-system/README.md`:**

\#\# Network Mode Management (v4.0 Separation Strategy)

We have consolidated network state management into a single, robust script to reliably switch between "VPN Mode" and "DNS Mode." This aligns with the principle of Infrastructure as Code, making the Control D dashboard the source of truth for filtering rules.

\*\*Location:\*\* \`scripts/network-mode-manager.sh\`

\#\#\# Usage

\* \*\*Enable Control D:\*\* \`./scripts/network-mode-manager.sh controld gaming\` (Use \`privacy\`, \`browsing\`, or any defined profile name.)

\* \*\*Enable Windscribe:\*\* \`./scripts/network-mode-manager.sh windscribe\` (This action stops Control D, disables IPv6 for leak protection, and resets the system DNS to DHCP/Empty.)

\* \*\*Check Status:\*\* \`./scripts/network-mode-manager.sh status\`

\> \*\*Note:\*\* This script replaces \`controld-manager\` and \`windscribe-controld\`. \*\*Do not\*\* use \`ctrld service\` or any other old management scripts directly, as they will disrupt the managed state.

4\. Analysis of Security and Robustness Improvements

The new design delivers significant advantages over the previous architecture:

| Improvement | Mechanism in the Script | Benefit |
| ----- | ----- | ----- |
| **Least Privilege Model** | The `ensure_prereqs` function checks `$EUID` and forces the script to fail if run as root. `sudo` is used only on a per-command basis (`networksetup`, `ctrld service`). | Prevents accidental system-wide damage, limits the scope of any potential script vulnerability, and increases security hygiene. |
| **Code Modularity** | Leveraging the external `./scripts/macos/ipv6-manager.sh` via the `set_ipv6` function. | Centralizes IPv6 logic. If the method for enabling/disabling IPv6 ever changes (e.g., adding support for Ethernet), the fix only needs to be applied in one place. |
| **Fail-Safe DNS Configuration** | The `start_controld` function uses `sleep 3` then explicitly calls `sudo networksetup -setdnsservers "Wi-Fi" "$LISTENER_IP"`. | Provides necessary redundancy. Even if `ctrld`'s internal configuration of macOS DNS settings hiccups, the script forces the DNS to point to the local listener, guaranteeing traffic is routed through the resolver. |
| **Clean State Principle** | The `stop_controld` function aggressively stops the service, kills lingering processes, and resets DNS to "Empty" *before* any mode switch. | Ensures that whether switching to Control D or Windscribe mode, the system starts from a known-good, neutral state, eliminating residual conflicts. |

