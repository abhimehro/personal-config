# SSH CHANGELOG

A focused history of the SSH setup in this repo. See the main `README.md` for the broader system version history.

## v3.0 – Dual-Agent SSH (1Password + Proton Pass)
- **Date:** 2026-02-03
- **Status:** Current
- **Highlights:**
  - Added Proton Pass support as an optional second SSH agent.
  - Created a dedicated Proton vault `SSH Keys` for SSH key storage.
  - Introduced paste-based key import script:
    - `scripts/ssh/op_to_proton_import.sh` (1Password → Proton, secure temp file workflow).
  - Added Proton SSH helper wrapper:
    - `scripts/ssh/proton_ssh_helpers.sh` (`start-agent`, `load-into-agent`, `import-key`).
  - Fish integration via `proton_pass_ssh.fish` with functions:
    - `pp_ssh_agent_start`, `pp_use_proton_agent`, `pp_load_proton_into_agent`, `pp_which_agent`.
    - Abbreviations: `pp-start`, `pp-load`, `pp-import`.
  - SSH config now exposes Proton-specific host aliases:
    - `github-proton` – GitHub via Proton agent.
    - `proton-*` – pattern for Proton-backed hosts.
  - Generic hostnames standardized to `dev-*` (e.g., `dev-mdns`, `dev-local`, `dev-auto`, `dev-vpn`).

## v2.1 – Generic `dev-*` Hostnames
- **Date:** 2026-02-03
- **Status:** Supersedes earlier `cursor-*` naming
- **Highlights:**
  - Renamed Cursor-specific hosts (`cursor-mdns`, `cursor-local`, `cursor-auto`, `cursor-vpn`) to generic, identity-neutral names:
    - `dev-mdns`, `dev-local`, `dev-auto`, `dev-vpn`.
  - Updated scripts and docs to match:
    - `scripts/test_ssh_connections.sh` now tests `dev-*`.
    - `scripts/ssh/smart_connect.sh` prefers `dev-mdns` → `dev-local` → `dev-auto` → `dev-vpn`.
    - `scripts/ssh/setup_aliases.sh` suggests `dev-*` aliases.
    - Main `README.md` quick-start and workflows now reference `dev-*`.
  - Legacy docs (`docs/ssh/*.md`) marked explicitly as describing the older `cursor-*` + 1Password-only configuration.

## v2.0 – 1Password-Managed SSH for Cursor IDE
- **Date:** 2025-08-04
- **Status:** Legacy but still valid if Proton is disabled
- **Highlights:**
  - Introduced 1Password SSH agent as the single source of truth for keys.
  - Established SSH config + agent files under `configs/ssh/`:
    - `configs/ssh/config`
    - `configs/ssh/agent.toml`
  - Added Cursor-focused host entries:
    - `cursor-mdns`, `cursor-local`, `cursor-auto`, `cursor-vpn`.
  - Created automation scripts:
    - `scripts/install_ssh_config.sh`
    - `scripts/sync_ssh_config.sh`
    - `scripts/verify_ssh_config.sh`
    - `scripts/test_ssh_connections.sh`
    - `scripts/ssh/smart_connect.sh`
    - `scripts/ssh/check_connections.sh`
    - `scripts/ssh/setup_verification.sh`
    - `scripts/ssh/diagnose_vpn.sh`
  - Documented in:
    - `docs/ssh/ssh_readme.md`
    - `docs/ssh/ssh_configuration_guide.md`
    - `docs/ssh/SSH_FIX_SUMMARY.md`

## v1.0 – Initial SSH Structure
- **Date:** 2025-04 (approx.)
- **Status:** Historical
- **Highlights:**
  - Basic SSH config under `configs/ssh/` with manual edits.
  - No 1Password or Proton Pass integration.
  - No generic naming; host definitions were machine/identity-specific.

---

**Current recommended path (v3.0):**
- 1Password remains the primary SSH agent.
- Proton Pass provides a second, optional agent (`SSH Keys` vault) with clear scripts, fish helpers, and dedicated host aliases.
- Generic `dev-*` hostnames keep configs portable across machines and workflows.
