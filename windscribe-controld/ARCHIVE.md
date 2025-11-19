# Windscribe + Control D Legacy/Archived Components

This directory contains both active documentation and legacy glue scripts
from earlier iterations of the Windscribe + Control D integration.

## Active (Reference) Docs

These files are still useful for understanding and manually testing the
VPN + DNS integration, even though day-to-day mode switching is now
handled by `scripts/network-mode-manager.sh`.

- `README.md` — High-level integration overview
- `setup-guide.md` — Detailed technical walkthrough
- `TROUBLESHOOTING.md` — Deep-dive troubleshooting guide
- `QUICK_REFERENCE.md` — Daily commands & diagnostics
- `WINDSCRIBE_DNS_SETUP.md` — Historical DNS tuning notes

## Legacy / Experimental Scripts

The following scripts are considered **legacy**. They were used during
earlier experiments (binding adjustments, DNS priority overrides, custom
LaunchDaemon attempts) and are kept for historical reference only:

- `controld-service-manager.sh` — Experimental VPN-compatible LaunchDaemon
- `fix-controld-config.sh` — Early listener/binding fix for Control D
- `fix-dns-priority.sh` — DNS priority override helper
- `test-vpn-integration.sh` — Older VPN integration test harness
- `verify-integration.sh` — Older verification wrapper

For v4.x and later, prefer the unified separation strategy:

- `scripts/network-mode-manager.sh` — Switches between Control D DNS and Windscribe VPN
- `scripts/network-mode-verify.sh` — Tight verification for each mode
- `scripts/network-mode-regression.sh` — Full end-to-end regression
- `controld-system/scripts/controld-manager` — Underlying Control D profile engine

## Safety Notes

- Do **not** mix these legacy scripts with `network-mode-manager.sh` in the
  same session; they may modify DNS, bindings, or services in ways that
  conflict with the separation strategy.
- If you need to study an old behavior, treat these as read-only examples
  and make any new experiments in separate, clearly-labeled scripts.
