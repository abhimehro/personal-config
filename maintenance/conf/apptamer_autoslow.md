# App Tamer AutoSlow Configuration

App Tamer stores per-process settings in its own preferences, not a plain text
file you can drop into this repo, so this doc is the source-of-truth checklist.
Apply each entry once via the App Tamer menu bar UI:

1. Open **App Tamer** > click the process in the list (or use **Show All
   Processes** to surface background daemons).
2. Set the behavior to **AutoSlow when not in use** (slows the process to
   near-0% CPU after it has been idle/background for the grace period).
3. For the always-background system daemons below, you can instead use **Slow
   down this process** outright since you never interact with them.

## Behavior key

- **AutoSlow** = slow only when the app is in the background / not focused.
- **Slow** = always throttle (use for daemons you never interact with).

## Target processes

### macOS system daemons (always Slow -- pure background analytics)

| Process                        | Behavior | Why                                                                                                                     |
| ------------------------------ | -------- | ----------------------------------------------------------------------------------------------------------------------- |
| `systemstats`                  | Slow     | Power/energy analytics; the trigger for this whole exercise. SIP-protected so cannot be disabled, but safe to throttle. |
| `mds` / `mds_stores`           | AutoSlow | Spotlight indexing. AutoSlow (not hard Slow) so search stays usable; lets it run when foregrounded.                     |
| `mdworker` / `mdworker_shared` | AutoSlow | Spotlight worker spawns. Same reasoning as `mds`.                                                                       |
| `photoanalysisd`               | Slow     | Photos face/scene analysis. Already disabled in `service_optimizer.sh`; AutoSlow is belt-and-suspenders if it respawns. |
| `mediaanalysisd`               | Slow     | Visual look-up / media analysis. Background only.                                                                       |
| `cloudphotod`                  | AutoSlow | iCloud Photos sync; AutoSlow so syncs still complete when active.                                                       |
| `bird`                         | AutoSlow | iCloud Drive sync daemon; AutoSlow to avoid stalling sync.                                                              |
| `backupd`                      | AutoSlow | Time Machine. AutoSlow so scheduled backups still run when foregrounded by the OS.                                      |
| `corespotlightd`               | AutoSlow | CoreSpotlight indexing.                                                                                                 |
| `suggestd`                     | Slow     | Siri suggestions; already disabled via `service_optimizer.sh`.                                                          |

### Resource-heavy apps (AutoSlow when not in use)

| Process                | Behavior | Why                                                                                              |
| ---------------------- | -------- | ------------------------------------------------------------------------------------------------ |
| Google Chrome / Helper | AutoSlow | Renderer/helper processes are the classic AutoSlow win; background tabs stop burning CPU.        |
| Brave Browser / Helper | AutoSlow | Same; you run Brave/Canary backends for Coherence X isolation.                                   |
| Google Chrome Canary   | AutoSlow | Background daily-build helper processes.                                                         |
| Slack                  | AutoSlow | Electron app, heavy when backgrounded.                                                           |
| Discord                | AutoSlow | Electron; idles poorly.                                                                          |
| Cursor / Code Helper   | AutoSlow | Electron + extension hosts. **Exclude** the language-server child if you want background builds. |
| Spotify                | AutoSlow | Leave the audio render thread alone -- App Tamer auto-detects active playback and won't slow it. |
| Microsoft Teams        | AutoSlow | Electron.                                                                                        |
| Notion                 | AutoSlow | Electron.                                                                                        |
| Figma                  | AutoSlow | GPU/CPU heavy when backgrounded.                                                                 |

### Do NOT slow (allow-list / exclusions)

Add these to App Tamer's exclusions so AutoSlow never touches them:

- `WindowServer`, `kernel_task`, `launchd` -- core OS, never throttle.
- `Windscribe` / `windscribe` -- VPN; throttling can drop the tunnel (your hard
  gate depends on it).
- `1Password` / `1PasswordHelper` -- security agent, keep responsive.
- Any active screen-recording / media-conversion job (ffmpeg) while running.
- `AutoRaise` -- your focus-follows-mouse helper must stay snappy.

## Notes

- App Tamer auto-detects audio/video playback and foreground use, so AutoSlow on
  Spotify/Chrome won't interrupt active playback.
- After applying, confirm `systemstats` shows a near-0% sampled CPU in App
  Tamer's process list when idle.
- Re-check this list after major macOS updates; Apple occasionally renames
  analytics daemons.
