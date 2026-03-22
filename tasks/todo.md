# 🛠️ Fix Control D "Maintenance is in progress" Error

**Purpose:** Fix the `network-mode-manager.sh` script to recover gracefully when `api.controld.com` is down (returning "Maintenance is in progress. Please try again later.").

**Security & Assumptions:**
- *Trust Boundary:* We act on data fetched locally, no new external unprivileged services are trusted.
- *Assumption:* Control D's DoH resolution servers (`dns.controld.com`) remain functional even when their configuration API (`api.controld.com`) is offline.
- *Threat Mitigated:* A denial-of-service in the upstream Control D configuration API breaks all basic local internet connectivity. By introducing an auto-fallback to standard DoH endpoints if the native configuration fetch fails, we ensure users retain ad-blocking and privacy via their Control D profile ID.

**Steps:**

- [x] Diagnose the root cause of `nm-vpn privacy` failure (identified as `api.controld.com` maintenance returning a 503).
- [x] Implement `generate_fallback_config()` in `scripts/lib/controld-profile.sh` to generate a static DoH `ctrld.toml` file automatically.
- [x] Modify `restart_with_native_profile()` in `scripts/lib/controld-service.sh` to catch failures during DNS initialization.
- [x] Upon failure, trigger the newly created static `.toml` via `restart_with_config()` to bypass the API fetch.
- [x] Ensure local end-to-end `make test` test cases are still passing.
