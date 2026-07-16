# Snyk Secure Development Hooks (operator guide)

Interactive docs outline for Secure at Inception + remediation commands in this repo.
(Canvas SDK was unavailable in the cloud agent environment; this markdown mirrors the docs-canvas structure.)

## Overview

| Item | Detail |
|------|--------|
| **Purpose** | Catch new SAST issues on agent-edited lines before the agent stops; remind about dependency health before installs |
| **Audience** | Cursor agents + human operators of `personal-config` |
| **Scope** | Project hooks under `.cursor/hooks*`; does not replace CI |

## Table of contents

1. [Architecture](#architecture)
2. [Hook events](#hook-events)
3. [Commands & skills](#commands--skills)
4. [Prerequisites](#prerequisites)
5. [Configuration](#configuration)
6. [Gotchas](#gotchas)
7. [References](#references)

## Architecture

```text
afterFileEdit ──► run-snyk-sai.sh ──► snyk_secure_at_inception.py
                                         │
                                         ├─ track modified line ranges
                                         └─ launch background snyk code test

stop ──────────► run-snyk-sai.sh ──► wait + filter vulns on edited lines
                                         │
                                         └─ followup_message → /snyk-batch-fix

beforeShellExecution ──► dependency-health-reminder.sh
                                         │
                                         └─ agent_message → snyk_package_health_check
```

## Hook events

### `afterFileEdit` / `stop` (Secure at Inception)

- Tracks code extensions and dependency manifests.
- On stop, only reports vulnerabilities whose line falls in agent-modified ranges.
- If CLI missing or unauthenticated: follow-up asks the agent to use MCP `snyk_code_scan` / `snyk_sca_scan`.
- `loop_limit: 3` caps the fix loop.

### `beforeShellExecution` (dependency health reminder)

- Matcher covers common package managers (`pip`, `npm`, `uv`, `cargo`, …).
- Always `permission: allow` — guidance only, no hard block.
- Script-side filters skip uninstall/list/help.

## Commands & skills

| Surface | When to use |
|---------|-------------|
| `/snyk-fix` | On-demand scan + fix highest-priority issue (code or SCA) |
| `/snyk-batch-fix` | Fix a table of vulns from the stop hook (no discovery scan) |
| `secure-dependency-health-check` | Before adding packages; compare candidates via `snyk_package_health_check` |

## Prerequisites

1. `python3` on PATH
2. Optional: `snyk` CLI (`npm i -g snyk` or Trunk’s snyk) + `snyk auth` / `SNYK_TOKEN`
3. Snyk MCP enabled in Cursor for MCP fallback scans and health checks

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `CURSOR_HOOK_DEBUG` | `0` | Debug logs from SAI Python hook |
| `MAX_STOP_CYCLES` | `3` (in script) | Max stop fix loops |
| `SCAN_WAIT_TIMEOUT` | `90` | Seconds waiting for background scan |

## Gotchas

- **Important:** Hooks fail open when `python3` or the SAI script is missing — agent work continues.
- **Warning:** Without Snyk auth, stop emits an MCP fallback follow-up rather than a vuln table.
- **Note:** Marketplace Snyk plugin hooks may also run; duplicate follow-ups are possible if both are enabled — prefer one source of truth (this project hook for `personal-config`).

## References

- Design: `docs/superpowers/specs/2026-07-16-snyk-secure-at-inception-hooks-design.md`
- Vendored scripts: `.cursor/hooks/snyk/`
- Upstream recipes: https://github.com/snyk/studio-recipes
- Related: Cursor Cloud secret-scan hooks (`make cursor-cloud-hooks`)
