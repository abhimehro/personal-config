# Archived LaunchAgents

Moved here during the 2026-07-09 LaunchAgent audit. Prefer restore from this
directory over recreating from memory.

| Plist                                    | Why archived                                                                                                                                                                                               | Restore notes                                                                                                                                                                                                                                                |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `com.personal.ctrld-network-watch.plist` | KeepAlive crash-loop (`runs` 1352+). Script called invalid `scutil --watch` (exits immediately). Also mutates Wi-Fi DNS / restarts `ctrld` and fights Control D profile switches + Colima `:53` ownership. | Do **not** re-enable until rewritten to use a real network-change watch (`scutil -w` / `networksetup` polling) **and** coordinated with `network-mode-manager` / Stream 1 Control D repair. Companion script: `configs/bin/archived/ctrld-network-watch.sh`. |
| (permute)                                | See `media-streaming/launchd/archived/com.speedybee.media.permute.plist` — exit 126 / non-executable.                                                                                                      | Restore from media-streaming archive only.                                                                                                                                                                                                                   |

**Control D note (2026-07-09):** Live host confirmed **WORKING /
local_fallback** (brew ctrld v1.5.3). Prefer `./scripts/controld-status.sh`;
repair only if BROKEN:
`sudo ./scripts/repair-controld-keepalive.sh --restart privacy`. CD Mode argv
must **not** include `--listen` (Lesson 0do). Colima coexistence uses Lima
`override.yaml`, not only `colima.yaml`.

Installed copies also live under `~/Library/LaunchAgents/archived/`.
