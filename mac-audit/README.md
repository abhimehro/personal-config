# mac-audit

![Mac Audit](https://github.com/abhimehro/personal-config/actions/workflows/mac-audit.yml/badge.svg)

A reusable, shellcheck-clean Mac system audit tool. Checks launch agent sprawl,
Homebrew drift, and risky `defaults` settings. Reruns after every system change
and runs automatically in GitHub Actions on every push.

## Structure

```
mac-audit/
├── audit.sh                        # Main entrypoint
├── lib/
│   ├── colors.sh                   # ANSI output helpers
│   ├── launch_agents.sh            # Scans Launch Agents & Daemons
│   ├── brew_audit.sh               # Homebrew package sprawl
│   └── defaults_audit.sh          # macOS security defaults
├── reports/                        # Gitignored timestamped reports
└── .gitignore
```

CI lives in the repo root: `.github/workflows/mac-audit.yml`
(ShellCheck on ubuntu + full audit on macos-14/15).

## Quick Start

```bash
git clone <your-remote-url> mac-audit
cd mac-audit
chmod +x audit.sh
./audit.sh
```

## Usage

```
./audit.sh [--report] [--ci] [--module launch|brew|defaults|all]

Flags:
  (none)          Run all modules, print to terminal
  --report        Also save a timestamped plaintext report to reports/
  --ci            Skip hardware-only checks (FileVault, systemsetup)
  --module <n>    Run only: launch | brew | defaults | all
  -h / --help     Show help
```

## GitHub Actions

One consolidated workflow (`.github/workflows/mac-audit.yml`):

| Job | Trigger | Runner | Purpose |
|---|---|---|---|
| `shellcheck` | Push/PR (`mac-audit/**`), weekly Mon, dispatch | ubuntu-latest | Lint audit scripts |
| `audit` | Same (after ShellCheck) | macos-14 + macos-15 | Full audit modules |

### CI vs. Local checks

| Check | Local | CI (`--ci` flag) |
|---|---|---|
| Launch agent scan | Full | Full |
| Homebrew sprawl | Full | Full |
| Gatekeeper | Full | Full |
| Application Firewall | Full | Full |
| SIP | Full | Full |
| Screen saver password | Full | Full |
| Remote SSH | Full | Full |
| FileVault | Full | Skipped (no disk encryption on GHA runners) |
| `systemsetup` re-check | Full | Skipped (requires interactive sudo) |

Audit reports are uploaded as **GitHub Actions artifacts** and retained 30 days.

## What Each Module Checks

### `launch` — Launch Agents & Daemons
Scans all four system directories. Flags Adobe, Google Keystone, Oracle Java,
temp-named labels, and orphaned plists (binary has been deleted).

### `brew` — Homebrew Package Sprawl
Outdated formulae count (warns at >5, fails at >20), total vs. leaf installs,
cask count (warns at >30), and a live list of running brew services.

### `defaults` — macOS Security Defaults
Gatekeeper, Application Firewall, screen saver password timing, Remote SSH,
Apple Remote Desktop, SIP, FileVault, and auto-diagnostics submission.

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | No failures detected |
| `1` | One or more checks flagged |

## Post-Install Hook (optional)

```bash
# .git/hooks/post-merge
#!/usr/bin/env bash
~/path/to/mac-audit/audit.sh --report
```

```bash
chmod +x .git/hooks/post-merge
```

## ShellCheck

```bash
shellcheck audit.sh lib/*.sh
```

## Adding a New Module

1. Create `lib/my_check.sh` with a `check_my_thing()` function
2. `source "$LIB_DIR/my_check.sh"` in `audit.sh`
3. Add `my_check.sh` to the `case` block in `run_module()`
4. Call `check_my_thing` in the `"all"` branch
