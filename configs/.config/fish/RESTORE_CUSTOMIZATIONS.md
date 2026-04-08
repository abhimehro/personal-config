# Fish Shell Customizations (Tide + Dracula)

This document captures the current known-good Fish setup and how to restore it after a fresh machine setup or shell reset.

## Source of Truth

The canonical Fish config for this repo lives at:

```text
~/dev/personal-config/configs/.config/fish/config.fish
```

Your live config should point to it via:

```text
~/.config/fish/ -> ~/dev/personal-config/configs/.config/fish/
```

## Prompt: Tide v6 (via Fisher)

Install or update plugins:

```fish
fisher update
```

If `fisher` is not installed yet:

```fish
curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source
fisher install jorgebucaran/fisher
fisher update
```

To reconfigure Tide interactively:

```fish
tide configure
```

## Dracula Theme Layering

The terminal look is intentionally layered:

* **Ghostty** handles the terminal color theme
* **Tide** handles the prompt via universal variables
* **Fish syntax highlighting** uses the Dracula Fish theme
* **fzf** and **bat** are styled from `config.fish`

## Fish Syntax Highlighting

Fish syntax colors are repaired on interactive startup by the helper:

```fish
__ensure_dracula_theme
```

That helper re-runs this command only when startup drift is detected:

```fish
fish_config theme choose "Dracula Official"
```

This is intentional because Fish syntax colors had occasionally drifted away from Dracula after startup.

## Tide Prompt Colors

Tide colors are stored in universal variables. Example Dracula-aligned values:

```fish
# Git segment
set -U tide_git_color_branch BD93F9
set -U tide_git_color_dirty F1FA8C
set -U tide_git_color_staged 50FA7B
set -U tide_git_color_stash FFB86C
set -U tide_git_color_untracked FF79C6

# Directory path
set -U tide_pwd_color_dirs F8F8F2
set -U tide_pwd_color_anchors BD93F9
set -U tide_pwd_color_truncated_dirs 6272A4

# Command duration + status
set -U tide_cmd_duration_color FFB86C
set -U tide_status_color 50FA7B
set -U tide_status_color_failure FF5555

# Context (user@host, shown for SSH/root)
set -U tide_context_color_default 8BE9FD
set -U tide_context_color_root FF5555
```

## Tool Theming from `config.fish`

`config.fish` currently sets:

* `BAT_THEME=Dracula`
* `FZF_DEFAULT_OPTS` with Dracula colors and `--style=full`
* `FZF_DEFAULT_COMMAND` and `FZF_CTRL_T_COMMAND` via `fd` when available

## SSH Agent Behavior

`config.fish` includes a health check that:

* prefers the 1Password SSH agent when its socket is available
* falls back to the macOS native SSH agent if needed

This keeps interactive shells and IDE terminals more stable.

## Safe Files to Edit

These are the main Fish files intended for manual edits:

* `configs/.config/fish/config.fish`
* `configs/.config/fish/fish_plugins`
* `configs/.config/fish/RESTORE_CUSTOMIZATIONS.md`
* `configs/.config/fish/functions/__ensure_dracula_theme.fish`
* `configs/.config/fish/functions/fish_greeting.fish`
* `configs/.config/fish/functions/git-mirror-clean.fish`
* `configs/.config/fish/functions/vibe.fish`
* `configs/.config/fish/functions/__run_editor.fish`

These are generally plugin-managed or machine-generated:

* `configs/.config/fish/conf.d/*.fish`
* `configs/.config/fish/functions/_fzf_*`
* `configs/.config/fish/functions/_tide_*`
* `configs/.config/fish/fish_variables`

## Verification

After making changes:

```fish
fish --no-config --no-execute ~/dev/personal-config/configs/.config/fish/config.fish
exec fish
```
