# Guarded Trunk Upgrades

`trunk upgrade` bumps every enabled linter to its latest release, including
versions held back on purpose. This repo (and the other Trunk repos under
`~/dev`) pin `pinact` at **4.1.1** because pinact v5 rejects the single-dash
`-format` flag that trunk plugins v1.11.0 still passes via `pinact_run.py`
(verified 2026-11-03: pinact 5.0.2 errors `unknown flag: -format`). Trunk
does not respect pin comments, so the pin must be re-enforced after every
upgrade.

## The guarded script

```bash
# All ~/dev repos with a .trunk/trunk.yaml
maintenance/bin/trunk_upgrade_guarded.sh

# Specific repos only
maintenance/bin/trunk_upgrade_guarded.sh ~/dev/ctrld-sync ~/dev/personal-config

# Override the pin target (e.g. when plugins finally emit --format)
TRUNK_PINACT_VERSION=5.0.2 maintenance/bin/trunk_upgrade_guarded.sh
```

Per repo, the script:

1. Requires a clean `.trunk/trunk.yaml` (no unstaged changes) unless `FORCE=1`.
2. Runs `trunk upgrade -y --no-progress`.
3. Reverts any `pinact` version above the pin back to the pin.
4. Validates the config with `trunk upgrade --dry-run`.
5. Commits **only** `.trunk/trunk.yaml` (never sweeps untracked files).
6. Pushes to `origin HEAD` via the `gh` credential helper over HTTPS, so it
   works even when the 1Password SSH agent is unavailable.

Log: `~/Library/Logs/maintenance/trunk_upgrade_guarded.log`

## When the pin can be lifted

Remove the pin (and the revert step) once trunk plugins emit `--format` for
pinact. Check by upgrading the `trunk-io/plugins` ref in `.trunk/trunk.yaml`
and running `trunk check` with pinact 5.x enabled; if it passes without the
`unknown flag` error, the guard is obsolete.

## Related

- `.trunk/trunk.yaml` carries the inline `PINACT-PIN` comment next to the
  enabled linter entry.
- `maintenance/bin/gitnexus_auto_sync_once.sh` handles the daily auto-sync;
  this guarded upgrade is intentionally manual (linters should not churn
  on a schedule without review).
