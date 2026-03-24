# Fish Shell Customizations (Tide + Dracula)

This document captures the current "known good" Fish setup and how to restore it.

## Prompt: Tide v6 (via Fisher)

Install/update plugins (including Tide):

```fish
fisher update
```

If `fisher` is not installed (fresh machine / disaster recovery):

```fish
curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source
fisher install jorgebucaran/fisher
fisher update
```

To reconfigure Tide's layout interactively:

```fish
tide configure
```

### Tide Dracula Colors

Tide manages prompt colors via `set -U` universal variables. Apply the Dracula palette:

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

## Theme: Dracula (syntax highlighting)

Syntax colors are managed by the `dracula/fish` theme, activated once via:

```fish
fish_config theme choose "Dracula Official"
```

This stores colors as universals — no need to set them in `config.fish`.

Tool-specific theming is also set in `config.fish`:

- **fzf**: `FZF_DEFAULT_OPTS` → Dracula color scheme (set only if not already defined)
- **bat**: `BAT_THEME` → `Dracula` (set only if not already defined)

## SSH Agent

`config.fish` includes a health check that uses 1Password's SSH agent when
available and falls back to macOS native agent if the socket is missing.
This prevents IDE background terminals from stalling (see `tasks/lessons.md` Lesson 0i).

## Greeting Function

A rotating time-based greeting function is defined inline in `config.fish`.

## Verifying Configuration

After making changes, reload Fish:

```fish
exec fish
```
