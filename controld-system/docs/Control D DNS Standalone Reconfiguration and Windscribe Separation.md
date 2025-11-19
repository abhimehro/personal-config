
# Problem Statement
Control D DNS and Windscribe VPN are currently intertwined through custom scripts and configuration paths, including Windscribe-specific Control D profiles and launchd setups. The goal is to make Control D a standalone, always-on DNS solution using DoH3 for all profiles (with IPv6 fully enabled) and to make Windscribe a separate, mutually exclusive mode where Control D is completely disabled and IPv6 is turned off to prevent leaks.
# Current State (Validated Observations)
* Control D service/process
    * `ps aux` shows an active `ctrld` process: `/opt/homebrew/bin/ctrld run --config=/etc/controld/ctrld.toml --skip_self_checks --iface=auto --homedir=/etc/controld`.
    * `lsof -nPi :53` shows no listeners on port 53, so the currently running `ctrld` is not binding to port 53 (or not exposing it in a way `lsof` can see).
    * `launchctl list` (non-sudo) shows no `ctrld`/`controld` jobs; the actual daemon is likely running as a system LaunchDaemon (root context).
* LaunchDaemon definition
    * ` /Library/LaunchDaemons/ctrld.plist` points to `/opt/homebrew/bin/ctrld run --config=/etc/controld/ctrld.toml --skip_self_checks --iface=auto --homedir=/etc/controld` (lines 10–20).
    * `RunAtLoad` is currently `false` and `Disabled` is `false` (lines 31–34), so auto-start semantics may not match the intended "always-on" behavior.
* Control D configuration files
    * User config: `~/.config/controld/ctrld.toml` exists and is a multi-profile configuration (lines 4–44):
        * Listener: `[listener.0] ip = "*********" port = 53` (local listener; masked but appears to be localhost style).
        * Upstreams: three profiles (`privacy_enhanced`, `browsing_privacy`, `gaming_optimized`) all with `type = "doh"` and `freedns.controld.com/<resolver_id>` endpoints.
        * Network: `[network.0]` includes both IPv4 and IPv6 CIDRs (`"*******/0", "::/0"`) and defaults `upstream = ["privacy_enhanced"]`.
    * System config: `/etc/controld/ctrld.toml` is referenced by the running process and LaunchDaemon, but a non-root file read failed; its exact contents, protocols, and listeners are currently unknown and must be inspected with `sudo`.
* Profile management scripts
    * `~/bin/ctrld-switch` is a thin wrapper that calls the repo script with `sudo`:
        * Delegates to `controld-system/scripts/controld-manager` with `sudo bash "$MANAGER_SCRIPT" switch "$1"` (lines 5, 23–24).
    * `controld-system/scripts/controld-manager` currently:
        * Treats `/etc/controld` as canonical (`CONTROLD_DIR="/etc/controld"` and uses `/etc/controld/ctrld.toml` and `/etc/controld/profiles/...` configs).
        * Generates per-profile configs under `/etc/controld/profiles/ctrld.<profile>.toml`, including Windscribe-focused changes:
        * Changes listener IP from localhost to a wildcard/all-interfaces value for VPN compatibility (`sed` on `ip = '*********'` to `ip = '*******'`, line 176–177).
        * Strips IPv6 CIDRs (removes `"::/0"`) to force IPv4-only behavior (lines 179–182).
        * Encodes protocol choices tightly coupled to Windscribe integration:
        * `gaming` → `doh3`, `privacy`/`browsing` → `doh` (lines 27–33).
        * Controls system DNS via `networksetup -setdnsservers Wi-Fi *********` and then logs that it is "skipping system DNS configuration to prevent Windscribe interference" (lines 240–243, note the internal inconsistency).
        * Implements emergency restore of original DNS servers from backups under `/etc/controld/backup`.
* Auxiliary Control D scripts
    * `scripts/macos/controld-ensure.sh`:
        * Treats Control D as a remote DNS IP (`CONTROL_D_DNS="*********"`) and enforces that DNS via `networksetup -setdnsservers` for `Wi-Fi` and `USB 10/100/1000 LAN` (lines 15–21, 39–45).
        * Validates via direct queries to `verify.controld.com` using `@"$CONTROL_D_DNS"` (lines 88–99).
        * Does not interact with the `ctrld` local listener directly, and assumes a DoH-backed remote resolver rather than a local port 53 proxy.
* IPv6 management
    * `scripts/macos/ipv6-manager.sh`:
        * Provides `disable`, `enable`, and `status` operations for IPv6 across all network services using `networksetup -setv6off` / `-setv6automatic` and sysctl tweaks to `net.inet6.ip6.accept_rtadv` (lines 13–28, 35–50, 56–71).
        * Currently documented as a Windscribe-oriented tool (usage examples mention "recommended with Windscribe", lines 93–100).
* System DNS state (non-privileged snapshot)
    * `scutil --dns` shows resolvers with a single masked nameserver IP (`nameserver[0] : *********`) and multiple scoped resolvers; the exact IP is redacted, but it is not obviously tied to `127.0.0.1` versus a Control D anycast IP.
    * `networksetup -getdnsservers Wi-Fi` shows a single configured server (`"*********"`).
    * There is no recognized Ethernet service (`networksetup` reports the Ethernet service name as invalid), so Wi-Fi is the only active interface in practice.
* Windscribe integration layer (repo state)
    * `windscribe-controld/README.md` and `windscribe-controld-setup.sh` document and enforce a combined Windscribe+Control D stack, including:
        * Expectation that Control D listeners bind to all interfaces (`*******:53`) so DNS can arrive through the VPN tunnel.
        * Guidance to set Windscribe DNS to "Local" or custom Control D IPs, and scripts that reconfigure system DNS after VPN connection.
    * Multiple helper scripts in `windscribe-controld/` and `controld-system/` encode assumptions about dual operation and contain Windscribe-specific hacks (binding IP changes, IPv6 stripping, explicit handling of utun interfaces, etc.).
# Target Architecture
* Clear separation of modes
    * Control D Mode (default):
        * `ctrld` runs as the only DNS controller on the system, binding port 53 on localhost.
        * All three profiles (privacy, browsing, gaming) use DoH3 for upstream resolution.
        * IPv6 is fully enabled on macOS and in Control D config, so both AAAA and A queries route through Control D without leaks.
        * System DNS (via `networksetup` / `scutil --dns`) points exclusively to the local Control D listener.
    * Windscribe Mode:
        * `ctrld` service is fully stopped and its LaunchDaemon is unloaded.
        * System DNS is reset to either DHCP/router defaults or Windscribe-managed DNS (ROBERT/custom), with no Control D entries.
        * IPv6 is disabled at the OS level (using `ipv6-manager.sh`) to avoid IPv6 leaks through non-VPN paths.
* Configuration ownership
    * Canonical Control D config will live under `~/.config/controld/ctrld.toml` with three named profiles and DoH3-only upstreams.
    * `/etc/controld` will no longer be the primary configuration home; if needed for `ctrld service` semantics, it will either be a thin wrapper/symlink to the user config or removed in favor of the user-level config that `ctrld service` can explicitly point at.
* Service management
    * The `ctrld` LaunchDaemon will be reinstalled via `sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks`, ensuring that the auto-start definition uses the user-level config and the intended listener.
    * Auto-start on boot will be enabled; only Control D Mode will keep this LaunchDaemon loaded.
    * Windscribe Mode will explicitly `sudo ctrld service stop` (or `service uninstall` if needed) so no `ctrld` processes run while Windscribe is active.
* Profile switching
    * `ctrld-switch` will be simplified to:
        * Map `privacy|browsing|gaming` to profile IDs and upstream names.
        * Update the `upstream = [...]` line in `[network.0]` of `~/.config/controld/ctrld.toml` to the desired profile.
        * Trigger a non-disruptive reload (`sudo ctrld reload`), with a fallback to `sudo ctrld service restart` if reload is unavailable.
        * Perform basic verification (dig via localhost, whoami.controld, and scutil snapshot) after switching.
    * All Windscribe-specific logic (binding to all interfaces, custom DNS changes, utun detection) will be removed from the profile switch path.
* Switching scripts (high-level behavior)
    * `enable-controld.sh` (Control D Mode):
        * Ensure IPv6 is enabled (`ipv6-manager.sh enable`).
        * Start or restart the `ctrld` service pointing at `~/.config/controld/ctrld.toml`.
        * Set Wi-Fi (and any active interfaces) DNS servers to the local Control D listener (e.g., `127.0.0.1`).
        * Flush DNS caches and run verification commands.
    * `disable-controld-for-windscribe.sh` (Windscribe Mode):
        * Stop the `ctrld` service and ensure no `ctrld` processes remain.
        * Reset DNS for Wi-Fi to `Empty` (DHCP/router) or to Windscribe’s recommended settings.
        * Disable IPv6 on all interfaces via `ipv6-manager.sh disable`.
        * Flush DNS caches and provide guidance that Windscribe can now be started.
    * `switch-controld-profile.sh` (Control D-only profile switcher):
        * Prompt for profile (1/2/3 or named), validate against a fixed allowlist.
        * Edit `~/.config/controld/ctrld.toml` to change `upstream = [...]` to the corresponding upstream name.
        * Reload/restart `ctrld` and run basic verification.
# Implementation Plan
## Phase 0: Deep-Dive Validation (Before Any Changes)
* Inspect system-level Control D configuration and service state
    * Use `sudo` commands (to be run manually by you) to:
        * List active LaunchDaemons: `sudo launchctl list | grep ctrld` and confirm the label actually in use.
        * Examine `/etc/controld` contents, especially `ctrld.toml` and any `profiles/ctrld.*.toml` files, to see:
        * Current listener IP/port.
        * Upstream endpoints and `type` (`doh` vs `doh3`).
        * IPv6-related CIDRs and policies.
        * Confirm whether `ctrld` is currently managing DNS via system DNS settings or acting purely as a local proxy.
* Confirm user-level Control D config status
    * Verify that `~/.config/controld/ctrld.toml` is unused today by checking whether `ctrld` references it anywhere in logs or service definitions.
    * Decide whether to treat `~/.config/controld/ctrld.toml` as the starting point for the new canonical config or to rebuild it from the current `/etc/controld/ctrld.toml`.
* Inventory Windscribe integration scripts and their actual use
    * Check whether any LaunchAgents or cron-like mechanisms currently invoke:
        * `scripts/macos/controld-ensure.sh`.
        * `windscribe-controld-setup.sh`.
        * `controld-system/scripts/controld-manager` directly.
    * Document which of these are actually in use (vs. historical artifacts) so we can deprecate them cleanly rather than accidentally breaking an active workflow.
## Phase 1: Remove Windscribe-Specific Coupling from Control D
* Decouple configuration paths
    * Choose a single canonical config location (recommended: `~/.config/controld/ctrld.toml`), then:
        * If `/etc/controld/ctrld.toml` differs materially, capture a sanitized backup in the repo for reference.
        * Plan to either:
        * Reinstall the service via `sudo ctrld service uninstall` followed by `sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks`, or
        * Adjust the LaunchDaemon (if required) so it points at the user-level config instead of `/etc/controld`.
* Decommission Windscribe-aware profile manager
    * Update `~/bin/ctrld-switch` to stop delegating to `controld-manager` and instead operate directly on `~/.config/controld/ctrld.toml` plus `ctrld reload/service restart`.
    * Move `controld-system/scripts/controld-manager` and related `/etc/controld/profiles` usage into an "archive" or clearly-labeled legacy section, with comments noting they are no longer part of the active path.
    * Remove Windscribe-specific behaviors from the active profile-switch path, including:
        * Binding listeners to all interfaces specifically for VPN.
        * Stripping IPv6 CIDRs (`"::/0"`).
        * Emergency DNS restore logic that assumes Windscribe integration.
* Retire Windscribe+Control D glue scripts
    * Mark `windscribe-controld` directory as legacy and ensure none of its scripts are invoked from active LaunchAgents or other automation.
    * If any of these scripts are still actively used, clearly scope them to a "Windscribe Mode" only flow that is separate from the new standalone Control D configuration.
## Phase 2: Rebuild Control D as a Standalone DoH3 Service
* Normalize and harden `~/.config/controld/ctrld.toml`
    * Ensure a single `[listener.0]`:
        * `ip` set to localhost (e.g., `127.0.0.1`).
        * `port = 53`.
    * For each upstream profile (`privacy_enhanced`, `browsing_privacy`, `gaming_optimized`):
        * Set `type = "doh3"` to enforce DoH3/QUIC.
        * Verify endpoints (`freedns.controld.com/<resolver_id>`) and bootstrap IPs are still valid.
        * Optionally tune `timeout` and logging for stability under DoH3.
    * Confirm `[network.0]` includes both IPv4 and IPv6 CIDRs (`0.0.0.0/0` and `::/0`) so IPv6 queries are captured.
* Reinstall or fix the `ctrld` LaunchDaemon
    * Use `sudo ctrld service uninstall` followed by `sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks` to:
        * Generate a clean `ctrld` LaunchDaemon using the user-level config.
        * Ensure `RunAtLoad` is true and KeepAlive semantics are appropriate.
    * Verify that the new LaunchDaemon is present under `/Library/LaunchDaemons` and points at the desired config path.
* Align system DNS with the local listener
    * Use `networksetup -setdnsservers` so Wi-Fi (and any other active services) resolves against the local Control D listener (e.g. `127.0.0.1`).
    * Confirm via `scutil --dns` that resolver #1 uses the local listener IP and that no stale Windscribe/Control D anycast IPs remain.
    * Flush DNS caches and validate resolution using `dig` and `whoami.control-d.net`.
## Phase 3: Implement Clean Mode Switching Scripts
* Implement `enable-controld.sh`
    * Responsibilities:
        * Enable IPv6 on all interfaces via `ipv6-manager.sh enable`.
        * Start (or restart) the `ctrld` service if not running, using the cleaned `ctrld.toml`.
        * Enforce DNS settings on active network services to point to the local Control D listener.
        * Flush DNS caches, then run verification steps:
        * `launchctl list | grep ctrld` (or equivalent) to confirm the daemon is loaded.
        * `lsof -nPi :53` to confirm Control D holds port 53.
        * `scutil --dns` to verify nameservers point at the local listener.
        * `dig +short whoami.control-d.net` and `dig AAAA example.com` to ensure both IPv4 and IPv6 traffic use Control D.
    * Security/robustness considerations:
        * Use strict error checking (`set -euo pipefail`).
        * Validate that expected binaries (`ctrld`, `networksetup`, `dig`) exist before use.
        * Log each step and fail loudly if any verification check fails.
* Implement `disable-controld-for-windscribe.sh`
    * Responsibilities:
        * Stop `ctrld` via `sudo ctrld service stop` (or `uninstall` only if necessary) and confirm no `ctrld` processes remain.
        * Use `networksetup -setdnsservers Wi-Fi Empty` (and similar for other active services) to return DNS control to DHCP/router or Windscribe.
        * Disable IPv6 on all interfaces via `ipv6-manager.sh disable`.
        * Flush DNS caches and verify:
        * `launchctl list` (system level) shows no active `ctrld` jobs.
        * `lsof -nPi :53` shows no Control D listeners on port 53.
        * `scutil --dns` shows no Control D resolvers.
        * Print explicit messaging that the system is now ready for Windscribe to manage DNS.
    * Security/robustness considerations:
        * Carefully handle failure of any single step (e.g., if `ctrld` is not running, do not exit in an inconsistent state).
        * Avoid leaving mixed DNS configurations (e.g., some interfaces still pointing at localhost while `ctrld` is stopped).
* Implement `switch-controld-profile.sh`
    * Responsibilities:
        * Provide an interactive menu (1/2/3) or accept a profile name (`privacy`, `browsing`, `gaming`).
        * Map choices to upstream names in `~/.config/controld/ctrld.toml` and update the `[network.0] upstream = [...]` line; optionally, keep comments documenting each resolver ID.
        * Reload `ctrld` in-place via `sudo ctrld reload`, and fall back to `sudo ctrld service restart` if reload fails.
        * Perform quick verification (`dig @127.0.0.1 whoami.control-d.net` or a profile-specific test) and display status to the user.
    * Security/robustness considerations:
        * Use a fixed allowlist of profiles; reject arbitrary values to avoid accidental misconfiguration.
        * Ensure file editing is atomic (e.g., write to a temp file and move into place) to prevent partial `ctrld.toml` updates.
## Phase 4: Verification and Documentation
* Verification in Control D Mode
    * Confirm the checklist you outlined:
        * `launchctl list | grep ctrld` shows the daemon loaded (system context).
        * `lsof -nPi :53` shows the Control D process bound to port 53.
        * `scutil --dns` shows only the local Control D listener as nameserver.
        * `dig +short whoami.control-d.net` returns a Control D IP.
        * `dig AAAA example.com` confirms IPv6 resolution through Control D.
        * All three profiles are documented and verified as using DoH3 upstreams.
* Verification in Windscribe Mode
    * With `disable-controld-for-windscribe.sh` run:
        * No `ctrld` jobs in `launchctl` and no listeners on port 53.
        * `scutil --dns` shows no Control D entries; DNS is under Windscribe/router control.
        * `networksetup -getv6dnsservers Wi-Fi` (and general IPv6 status) confirm IPv6 is effectively disabled.
        * Windscribe connects and ROBERT/custom DNS behaves correctly.
* Documentation updates
    * Update `controld-system/README.md`, `QUICKREF.md`, and WARP.md sections to reflect:
        * DoH3-only upstreams.
        * New mode-switching scripts and how to use them.
        * The explicit separation between Control D Mode and Windscribe Mode, including IPv6 behavior in each.
    * Mark the `windscribe-controld` directory and `controld-manager` as legacy/archived, with clear notes that they are not used in the new design.
# Security Considerations
* Root privilege boundary
    * All changes that touch `/Library/LaunchDaemons`, `/etc/controld`, `networksetup`, or `ctrld service` must run under `sudo`; scripts will:
        * Refuse to run as plain root for safety (mirroring the pattern in `controld-ensure.sh`).
        * Prompt for `sudo` only for specific operations instead of running the entire script as root.
* DNS integrity and leak prevention
    * Control D Mode:
        * Enforces a single, local listener for DNS and ensures both IPv4 and IPv6 query paths go through Control D.
        * Avoids partial configurations where some interfaces use Control D and others bypass it.
    * Windscribe Mode:
        * Disables Control D completely and turns off IPv6, preventing mixed-transport leak scenarios.
* Failure handling
    * Scripts will:
        * Fail fast if core operations (service start/stop, DNS reconfiguration) fail, leaving logs and clear guidance.
        * Provide emergency recovery instructions (e.g., restore DHCP DNS, disable Control D) similar to the existing `emergency_recovery` logic but without Windscribe coupling.
