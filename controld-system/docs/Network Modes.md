 # Network Modes

**Last Updated:** 2025-11-24  
**Status:** ✅ Active (v4.1 Separation Strategy)

## Overview

This repository defines two primary network modes for macOS:

* **Control D DNS mode (“DNS mode”)**
* **Windscribe VPN mode (“VPN mode”)**

Network state is coordinated by:

 `scripts/network-mode-manager.sh` *– top-level switch between DNS and VPN modes* `controld-system/scripts/controld-manager` – low-level Control D profile manager

The goal is to keep **DNS mode** and **VPN mode** clearly separated:

 *In* *DNS mode**, Control D is responsible for DNS, IPv6 is enabled, and Windscribe should be disconnected.
 *In* *VPN mode**, Windscribe is responsible for network routing and DNS, Control D is stopped, and IPv6 is disabled for leak protection.

&gt; **Preferred entrypoint:** Use `scripts/network-mode-manager.sh` for day‑to‑day switching.  
&gt; Use `controld-manager` directly only when debugging or doing low-level Control D work.

---

## Quick Commands

Assumptions:

 *Repository cloned to:* `~/Documents/dev/personal-config`


 Commands run from the repository root

```bash
cd ~/Documents/dev/personal-config

# Everyday browsing (Control D DNS mode, browsing profile)
./scripts/network-mode-manager.sh controld browsing

# High-privacy mode (Control D DNS mode, privacy profile)
./scripts/network-mode-manager.sh controld privacy

# Gaming (Control D DNS mode, gaming profile)
./scripts/network-mode-manager.sh controld gaming

# Windscribe VPN mode (Control D off, IPv6 disabled, DNS reset)
./scripts/network-mode-manager.sh windscribe

# Show current mode and DNS/IPv6 status
./scripts/network-mode-manager.sh status

# Full regression: Control D → Windscribe with verification
./scripts/network-mode-regression.sh browsing
 Modes
Control D DNS Mode (⁠controld)
Command:
 ./scripts/network-mode-manager.sh controld [profile]
# profiles: privacy | browsing | gaming (default: browsing)
 What it does:
	•	Ensures prerequisites (macOS, ⁠ctrld, ⁠networksetup, IPv6 manager script). 	•	Enables IPv6 via ⁠scripts/macos/ipv6-manager.sh enable. 	•	Stops any existing ⁠ctrld processes and cleans up DNS state. 	•	Delegates to ⁠controld-system/scripts/controld-manager:
 sudo ./controld-system/scripts/controld-manager switch &lt;profile&gt;
  	•	Runs optional verification (⁠scripts/network-mode-verify.sh) when present. 	•	Leaves Windscribe disconnected (user responsibility) so that Control D is the only DNS authority.
Profiles:
Profile
Resolver ID
Default protocol
Intended use
⁠privacy
⁠6m971e9jaf
DoH3/QUIC
Maximum privacy & security
⁠browsing
⁠rcnz7qgvwg
DoH3/QUIC
Everyday balanced browsing
⁠gaming
⁠1xfy57w34t7
DoH3/QUIC
Low-latency gaming sessions
Typical flows:
	•	Everyday: ⁠./scripts/network-mode-manager.sh controld browsing 	•	Sensitive work: ⁠./scripts/network-mode-manager.sh controld privacy 	•	Gaming (no VPN): ⁠./scripts/network-mode-manager.sh controld gaming
Windscribe VPN Mode (⁠windscribe)
Command:
 ./scripts/network-mode-manager.sh windscribe
 What it does:
	•	Stops Control D cleanly and resets Wi‑Fi DNS to DHCP (“Empty”). 	•	Disables IPv6 via ⁠scripts/macos/ipv6-manager.sh disable to reduce leak surface. 	•	Flushes DNS caches. 	•	Runs optional verification (⁠scripts/network-mode-verify.sh windscribe) when present.
In this mode:
	•	Windscribe is expected to be the active VPN and DNS provider. 	•	Control D is not running locally. 	•	IPv6 is disabled at
the macOS level for consistency and leak protection.
Typical flow:
	1.	From the repo root:
 ./scripts/network-mode-manager.sh windscribe
  	2.	Connect Windscribe via the native app. 	3.	When finished, switch back to a Control D DNS mode:
 ./scripts/network-mode-manager.sh controld browsing
 
Status & Verification
Check Current Network Status
 ./scripts/network-mode-manager.sh status
 Shows:
	•	Whether ⁠ctrld is running. 	•	Active resolver ID (best effort). 	•	Current Wi‑Fi DNS servers. 	•	IPv6 status for Wi‑Fi.
Full Regression (Control D → Windscribe)
 ./scripts/network-mode-regression.sh [profile]
# default profile: browsing
 Sequence:
	1.	Switch to Control D DNS mode with the given profile. 	2.	Verify Control D active state. 	3.	Switch to Windscribe VPN mode. 	4.	Verify Windscribe‑ready state. 	5.	Print a one‑line PASS/FAIL summary with total duration.
Use this after:
	•	macOS updates 	•	DNS/VPN configuration changes 	•	Adjustments to ⁠controld-manager or IPv6 handling
Relationship to ⁠controld-manager
The Network Mode Manager treats ⁠controld-system/scripts/controld-manager as the source of truth for Control D:
	•	It does not duplicate profile logic. 	•	It calls ⁠controld-manager switch &lt;profile&gt; whenever entering DNS mode. 	•	It relies on ⁠controld-manager for:
	▪	Profile selection and resolver IDs 	▪	Protocol choice (DoH3 vs DoH) 	▪	Config generation and symlinking (⁠/etc/controld/ctrld.toml) 	▪	Low-level DNS validation and logging
Advanced usage (optional):
From the repo root:
 # Status and health
sudo ./controld-system/scripts/controld-manager status
sudo ./controld-system/scripts/controld-manager test

# Manual profile switch (outside of network-mode-manager)
sudo ./controld-system/scripts/controld-manager switch browsing
sudo ./controld-system/scripts/controld-manager switch privacy doh
sudo ./controld-system/scripts/controld-manager switch gaming

# Emergency recovery (when DNS is badly broken)
sudo ./controld-system/scripts/controld-manager emergency
 Recommendation: For normal workflow, prefer
⁠./scripts/network-mode-manager.sh controld &lt;profile&gt;
and reserve direct ⁠controld-manager calls for troubleshooting.
Legacy DNS Commands
Older v3.x DNS scripts are kept for historical reference and fallback:
 sudo dns-privacy    # Legacy privacy mode
sudo dns-gaming     # Legacy gaming mode
 These are superseded by the v4.x Network Mode Manager:
	•	⁠./scripts/network-mode-manager.sh controld privacy 	•	⁠./scripts/network-mode-manager.sh controld gaming
Guideline:
	•	Do not mix legacy ⁠dns-* commands and ⁠network-mode-manager.sh in the same session. 	•	Prefer ⁠network-mode-manager.sh for all new work. 	•	Use legacy commands only when debugging older behavior or performing targeted regression checks.
 
---

## Suggested shell helpers (aliases/functions)

Below are ergonomic helpers so you can type short commands from **any** directory.

### Bash / Zsh functions

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Root of personal-config repo
NM_ROOT="$HOME/Documents/dev/personal-config"

nm-browse() {
    cd "$NM_ROOT" && ./scripts/network-mode-manager.sh controld browsing
}

nm-privacy() {
    cd "$NM_ROOT" && ./scripts/network-mode-manager.sh controld privacy
}

nm-gaming() {
    cd "$NM_ROOT" && ./scripts/network-mode-manager.sh controld gaming
}

nm-vpn() {
    cd "$NM_ROOT" && ./scripts/network-mode-manager.sh windscribe
}

nm-status() {
    cd "$NM_ROOT" && ./scripts/network-mode-manager.sh status
}

nm-regress() {
    # Full regression using browsing profile
    cd "$NM_ROOT" && ./scripts/network-mode-regression.sh browsing
}

nm-cd-status() {
    # Low-level Control D status
    cd "$NM_ROOT" && sudo ./controld-system/scripts/controld-manager status
}
 Usage examples:
 nm-browse    # Control D DNS mode (browsing)
nm-privacy   # Control D DNS mode (privacy)
nm-gaming    # Control D DNS mode (gaming)
nm-vpn       # Windscribe VPN mode
nm-status    # Show current mode/DNS/IPv6
nm-regress   # Full regression run
nm-cd-status # Detailed Control D status