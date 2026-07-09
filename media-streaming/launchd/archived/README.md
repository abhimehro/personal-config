# Archived media LaunchAgents

| Plist                               | Why archived                                                                                                                                                                                              | Restore notes                                                                                             |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `com.speedybee.media.permute.plist` | User-requested stale. Was KeepAlive-crash-looping with exit 126 because `launch-permute.sh` was not executable (`Permission denied`). Permute 4 GUI watch-folder is better launched manually when needed. | `chmod +x media-streaming/scripts/launch-permute.sh`, move plist back to `../`, then `sync-launchagents`. |

Installed copy:
`~/Library/LaunchAgents/archived/com.speedybee.media.permute.plist`.
