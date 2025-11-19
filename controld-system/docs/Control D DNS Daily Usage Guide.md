# Control D DNS Daily Usage Guide

This guide summarizes the day-to-day workflows for using the Control D + Windscribe "Separation Strategy" on macOS. It assumes the Phase 1 implementation is in place, including:

- `scripts/network-mode-manager.sh`
- `scripts/network-mode-verify.sh`
- `scripts/network-mode-regression.sh`
- Updated maintenance scripts under `controld-system/` and `scripts/macos/`.

The core idea: **Control D DNS mode** and **Windscribe VPN mode** are mutually exclusive and each is optimized to work independently.

- **Control D Mode (DNS Mode)**
  - `ctrld` is the only DNS controller.
  - DNS is encrypted and filtered according to your Control D profile.
  - IPv6 is **enabled**.

- **Windscribe Mode (VPN Mode)**
  - `ctrld` is **stopped** and port 53 is free.
  - DNS is managed by DHCP/Windscribe (e.g. ROBERT/custom DNS).
  - IPv6 is **disabled** to prevent leaks outside the VPN tunnel.

---

## Profiles and When to Use Them

Profiles are defined in `scripts/network-mode-manager.sh` and mapped to Control D resolver IDs:

- `privacy` → `6m971e9jaf`
  - Maximum privacy/security, more aggressive blocking.
- `browsing` → `rcnz7qgvwg`
  - Balanced privacy vs compatibility.
  - Recommended default for most day-to-day browsing.
- `gaming` → `1xfy57w34t7`
  - Minimal filtering, tuned for low latency and fewer false positives.

These profile names are what you pass to the manager and regression scripts.

---

## Core Commands and When to Use Them

### 1. Network Mode Manager

**Script:** `scripts/network-mode-manager.sh`

This is the primary entry point for switching modes.

```bash
# Switch to Control D DNS mode
./scripts/network-mode-manager.sh controld browsing
./scripts/network-mode-manager.sh controld privacy
./scripts/network-mode-manager.sh controld gaming

# Switch to Windscribe VPN mode (Control D off, IPv6 off, DNS reset)
./scripts/network-mode-manager.sh windscribe

# Show current status
./scripts/network-mode-manager.sh status
```

#### What happens in `controld <profile>` mode

- Enables IPv6 (via `scripts/macos/ipv6-manager.sh enable`).
- Stops any existing `ctrld` instance and resets Wi-Fi DNS to `Empty`.
- Starts `ctrld` in service mode with `--cd <UID>`, letting the Control D cloud dashboard drive protocol and filtering.
- Binds the listener to `127.0.0.1` and sets Wi-Fi DNS to `127.0.0.1`.
- Flushes DNS caches.
- Prints a one-shot status snapshot.
- Automatically runs `scripts/network-mode-verify.sh controld` to validate the "Control D Active" checklist.

#### What happens in `windscribe` mode

- Stops `ctrld` and kills any lingering `ctrld` processes.
- Resets Wi-Fi DNS to `Empty`, allowing DHCP/Windscribe to own DNS.
- Disables IPv6 for all relevant network services via `ipv6-manager.sh disable`.
- Flushes DNS caches.
- Prints a status snapshot.
- Automatically runs `scripts/network-mode-verify.sh windscribe` to validate the "Windscribe Ready" checklist.

#### When to use these commands

- **Use `controld <profile>`** when you want encrypted, filtered DNS via Control D without a VPN:
  - `controld browsing` → default daily browsing.
  - `controld privacy` → high-security tasks (banking, sensitive work).
  - `controld gaming` → gaming/streaming sessions.

- **Use `windscribe`** when you want Windscribe to own routing + DNS:
  - Before connecting Windscribe, run `./scripts/network-mode-manager.sh windscribe`.
  - Then open the Windscribe app and connect.

- **Use `status`** any time you want a quick view of:
  - Whether `ctrld` is running.
  - Current resolver ID (best-effort from `ctrld status`).
  - Wi-Fi DNS servers.
  - IPv6 state on Wi-Fi.

---

### 2. Verification Checklists

**Script:** `scripts/network-mode-verify.sh`

This script runs the tight checklists for each mode and prints both human-readable results and a machine-friendly `SUMMARY` line.

```bash
# Verify Control D Active state
./scripts/network-mode-verify.sh controld

# Verify Windscribe Ready state
./scripts/network-mode-verify.sh windscribe
```

#### Control D Active checklist (controld)

- Confirms `ctrld` LaunchDaemon is loaded (`launchctl list | grep ctrld`).
- Confirms `ctrld` is bound to port 53 (`lsof -nPi :53 | grep ctrld`).
- Confirms resolver #1 nameserver matches the local listener IP (127.0.0.1).
- Resolves `whoami.control-d.net`.
- Performs an IPv6 AAAA lookup for `example.com` (sanity check that IPv6 resolution is working).
- Prints:

  ```text
  SUMMARY TS=... MODE=controld RESULT=PASS
  ```

#### Windscribe Ready checklist (windscribe)

- Ensures no `ctrld` LaunchDaemon is loaded.
- Ensures `ctrld` is not bound to port 53.
- Ensures resolver #1 nameserver is **not** the local Control D listener.
- Confirms IPv6 is reported as Off for Wi-Fi.
- Prints:

  ```text
  SUMMARY TS=... MODE=windscribe RESULT=PASS
  ```

**When to use:**

- After switching modes, if you want an extra, explicit verification.
- When debugging DNS or IPv6 issues.
- In CI or automation, by checking the `SUMMARY` lines and exit codes.

---

### 3. Full End-to-End Regression

**Script:** `scripts/network-mode-regression.sh`

**Make target:** `make control-d-regression`

```bash
# Direct invocation
./scripts/network-mode-regression.sh browsing

# Or via Makefile
make control-d-regression
```

This runs a full sequence:

1. Switch to Control D DNS mode using the specified profile (`browsing` by default).
2. Run `network-mode-verify.sh controld`.
3. Switch to Windscribe VPN mode.
4. Run `network-mode-verify.sh windscribe`.
5. Print a final summary with total duration, e.g.:

   ```text
   SUMMARY TS=... MODE=regression PROFILE=browsing RESULT=PASS DURATION_SECONDS=37
   ```

**When to use:**

- After system updates (macOS, Homebrew, ctrld, Windscribe, etc.).
- After changing Control D dashboard settings.
- After editing any of the network-mode scripts.
- When you want to assert the full DNS → VPN pipeline is still healthy.

---

### 4. Maintenance and Health Scripts

These are Separation-Strategy aware and delegate to the unified verification logic.

#### `controld-system/health-check.sh`

```bash
controld-system/health-check.sh
```

- Uses `network-mode-verify.sh controld` under the hood.
- Prints an overall status:

  ```text
  Overall Status: HEALTHY ✓
  SUMMARY TS=... MODE=health-check RESULT=PASS
  ```

or:

  ```text
  Overall Status: UNHEALTHY ✗
  SUMMARY TS=... MODE=health-check RESULT=FAIL
  ```

Use this when you want a **simple health snapshot** of Control D DNS mode.

#### `controld-system/baseline-test.sh`

```bash
controld-system/baseline-test.sh
```

- Also wraps `network-mode-verify.sh controld`.
- Prints:

  ```text
  Result: ALL TESTS PASSED ✓
  SUMMARY TS=... MODE=baseline-test RESULT=PASS
  ```

or:

  ```text
  Result: Baseline verification FAILED ✗
  SUMMARY TS=... MODE=baseline-test RESULT=FAIL
  ```

Use this as a **quick baseline test** (e.g. before/after changes, or part of manual checklists).

---

### 5. Login Enforcement (LaunchAgent)

**Script:** `scripts/macos/controld-ensure.sh`

This script is designed to run at login via a LaunchAgent and is now Separation-Strategy aware:

- Ensures the system is in Control D DNS mode using the `browsing` profile:

  ```bash
  scripts/macos/controld-ensure.sh
  ```

- Internally calls:
  - `scripts/network-mode-manager.sh controld browsing`
  - `scripts/network-mode-verify.sh controld`

- Logs to: `~/Library/Logs/controld-ensure.log`.

You typically do **not** need to run this manually, but it’s a safe way to re-enforce Control D mode after login if needed.

---

## Recommended Workflows by Scenario

### Scenario A: Normal Day with DNS Privacy Only

Goal: Encrypted, filtered DNS via Control D; no VPN.

1. Switch to Control D DNS mode (browsing profile):

   ```bash
   ./scripts/network-mode-manager.sh controld browsing
   ```

2. Optionally run a verification:

   ```bash
   ./scripts/network-mode-verify.sh controld
   ```

3. Browse normally. IPv6 is enabled and DNS flows through Control D.

To adjust filtering level:

```bash
./scripts/network-mode-manager.sh controld privacy   # stricter
./scripts/network-mode-manager.sh controld gaming    # more permissive
```

### Scenario B: Windscribe VPN Session

Goal: Windscribe owns routing + DNS, with no Control D interference.

1. Prepare the system for Windscribe:

   ```bash
   ./scripts/network-mode-manager.sh windscribe
   ```

   This stops Control D, frees port 53, sets DNS to Empty, and disables IPv6.

2. Open the Windscribe app and connect.

3. When finished, return to Control D DNS mode as needed:

   ```bash
   ./scripts/network-mode-manager.sh controld browsing
   ```

### Scenario C: After System or Config Changes

Goal: Confirm the entire DNS → VPN stack is still healthy.

1. Run the full regression (browsing profile):

   ```bash
   make control-d-regression
   # or
   ./scripts/network-mode-regression.sh browsing
   ```

2. Check that:

   ```text
   SUMMARY ... MODE=regression PROFILE=browsing RESULT=PASS
   ```

If it fails, run the individual verifiers:

```bash
./scripts/network-mode-verify.sh controld
./scripts/network-mode-verify.sh windscribe
```

### Scenario D: Something Feels Off (DNS / IPv6)

If you *expect* to be in Control D DNS mode:

```bash
./scripts/network-mode-verify.sh controld
controld-system/health-check.sh
```

If you *expect* to be in Windscribe mode:

```bash
./scripts/network-mode-verify.sh windscribe
```

These will tell you whether the system state matches your expectations.

---

## Summary

- Use `network-mode-manager.sh` to switch modes and profiles.
- Use `network-mode-verify.sh` for deep checklists and `SUMMARY` lines.
- Use `network-mode-regression.sh` / `make control-d-regression` after changes.
- Use `health-check.sh` and `baseline-test.sh` as quick maintenance endpoints.
- Let `controld-ensure.sh` keep Control D mode correct at login.

This setup gives you a clean, auditable separation between **DNS Mode** (Control D) and **VPN Mode** (Windscribe), with clear commands and checklists for every common scenario.