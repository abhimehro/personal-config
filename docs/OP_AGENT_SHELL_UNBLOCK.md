# 1Password agent/subagent shell unblock (2026-07-09)

## Root cause

Three independent 1Password integration points could block Cursor agent/subagent shells:

1. **Cursor 1Password plugin hook** (`beforeShellExecution` → `validate-mounted-env-files`)
   - In default mode, scans all 1Password Environments mounts under the workspace.
   - Workspace `/Users/speedybee/dev` includes `repoprompt-ce/version.env`, which is a **regular file**, not a FIFO mount → hook returns `permission: deny` and blocks shell.
2. **`op plugin` shell aliases** (`alias brew="op plugin run -- brew"` in `~/.config/op/plugins.sh`)
   - When sourced in interactive shells, `brew` (and similar) can trigger biometric/GUI auth that agents cannot complete.
3. **Fish login sets `SSH_AUTH_SOCK` to the 1Password SSH agent**
   - Background/agent shells have no UI for Touch ID; SSH operations can hang waiting for approval.
4. **Broken `~/.zprofile` symlink** pointed at removed `Documents/dev 2/personal-config/...`, so login zsh could not load managed profile.

## Fix (env-gated; interactive UX preserved)

| Change | Path | Effect |
|--------|------|--------|
| Gate `op` plugin aliases | `~/.config/op/plugins.sh` + `personal-config/configs/op/plugins.sh` | Skip aliases when `CURSOR_AGENT`/`CI`/non-TTY, or `OP_AGENT_SKIP=1`. `OP_AGENT_SKIP=0` forces aliases on. |
| Source plugins from zsh | `~/.zshrc` + managed `.zshrc` | Ensures gate is applied when zsh loads plugins. |
| Gate 1Password SSH sock | `~/.config/fish/config.fish` (+ managed copy) | Agents/CI/non-interactive fish keep macOS `SSH_AUTH_SOCK`; interactive fish still uses 1Password agent. |
| Workspace configured mode | `/Users/speedybee/dev/.1password/environments.toml` with `mount_paths = []` | Stops multi-repo workspace deny from stale/non-FIFO mounts. Per-project workspaces still validate their own mounts. |
| Repair zprofile | `~/.zprofile` → `~/dev/personal-config/configs/.zprofile` | Restores login profile after path move. |
| Fail-open user hook | `~/.cursor/hooks.json` + `hooks/allow-shell.sh` | Explicit allow for Shell while validating (plugin hooks still merge). |

## Overrides

- `OP_AGENT_SKIP=1` — force skip plugin aliases / (fish) 1Password SSH sock
- `OP_AGENT_SKIP=0` — force enable even in agent shells (may hang on biometric)

## Remaining risks

- `op plugin init` may overwrite `plugins.sh` — re-apply the gate after.
- Opening `/Users/speedybee/dev` as workspace intentionally skips Environments FIFO validation for that root; open a single project for strict mount checks.
- `repoprompt-ce/version.env` remains a regular file; re-enable as a 1Password FIFO destination if that project needs Environments.
- Interactive human shells still use 1Password SSH agent and (when plugins sourced) `op plugin` aliases — auth UX unchanged.
