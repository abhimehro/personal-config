# sync-launchagents

Stow-style deployer for the LaunchAgent plists under this repo. Replaces the
previous symlink approach with **real file copies** in
`~/Library/LaunchAgents/`, eliminating Mole's "orphan/stale login item" false
positives and `launchctl bootstrap` EIO 5 errors caused by dangling symlinks.

## Source-of-truth directories

The script discovers `*.plist` files under:

- `~/dev/personal-config/media-streaming/launchd/`
- `~/dev/personal-config/launch-agents/`

## Destination

- `~/Library/LaunchAgents/` (real files, mode 644)

## Quick start

```bash
# Sync everything (idempotent, checksum-driven)
sync-launchagents

# Preview without writes or launchctl mutations
sync-launchagents --dry-run --verbose

# Force redeploy even when checksums match (e.g. after macOS upgrade)
sync-launchagents --force

# Only sync a single label
sync-launchagents com.speedybee.media.server

# Print current loaded state
sync-launchagents --status

# Also remove com.speedybee.* plists in dest that no longer exist in repo
sync-launchagents --prune
```

The script is symlinked at `~/.local/bin/sync-launchagents` so it's on `$PATH`.

## What it does per plist

1. `plutil -lint` validation, broken plists are skipped.
2. SHA-256 checksum compare against the destination file.
3. If different (or destination is a symlink/missing):
   - `launchctl bootout gui/$UID/<label>` then wait for the label to clear.
   - `pkill -f` any lingering process whose `ProgramArguments` script path is
     still alive (prevents EIO 5).
   - `cp` from source to destination (atomic, mode 644).
   - `launchctl bootstrap gui/$UID <plist>`, falls back to `launchctl load -w`
     if bootstrap fails.
   - `launchctl enable gui/$UID/<label>`.
4. Writes a TSV manifest at `~/.local/state/sync-launchagents/manifest.tsv` for
   diff tracking.

## Why not symlinks?

- Mole's `clean_orphaned_app_data` and `show_user_launch_agent_hint_notice` flag
  broken symlinks as "stale login items" and remove them.
- `launchctl bootstrap` occasionally errors with `5: Input/output error` when
  handed a freshly re-pointed symlink.
- Real file copies survive `mo purge`, Time Machine restores, and most macOS
  upgrades.
- The git-tracked plists in this repo remain the canonical source. Edits flow
  `repo → sync-launchagents → ~/Library/LaunchAgents/`.

## Workflow

Whenever you edit a plist in the repo:

```bash
$EDITOR ~/dev/personal-config/media-streaming/launchd/com.speedybee.media.server.plist
sync-launchagents          # detects checksum diff, reloads only that one
```

## Mole interaction

`~/.config/mole/whitelist` already protects:

- `~/Library/LaunchAgents/com.speedybee.*.plist`
- `~/Library/LaunchAgents/com.abhimehrotra.*.plist`
- `~/dev/personal-config/**`
- `~/Library/Logs/{alldebrid-sync,media-renamer,media-server,media-server-error}.log*`

Run `mo clean --dry-run` after large repo refactors to verify nothing in this
set appears as a candidate.

## Troubleshooting

| Symptom                                                          | Likely cause                         | Fix                                                                           |
| ---------------------------------------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------- |
| `bootstrap failed for <label>`                                   | Old process still holding the label  | Script auto-retries with `load -w`. Verify with `sync-launchagents --status`. |
| `lint failed`                                                    | Malformed XML                        | `plutil -lint <plist>` to see the line, fix in repo, re-run.                  |
| Destination is still a symlink after sync                        | First-run conversion was interrupted | Re-run with `--force`.                                                        |
| Stale `com.speedybee.foo.plist` in dest after removing from repo | Orphan not auto-pruned               | `sync-launchagents --prune`.                                                  |

## Scheduling (optional)

If you want sync-on-login (e.g. after a Mole sweep), add a LaunchAgent that
calls this script with `RunAtLoad`. Keep the agent itself in the repo so it
sync's itself, the chicken-and-egg is fine because launchd will just reload it
next login.
