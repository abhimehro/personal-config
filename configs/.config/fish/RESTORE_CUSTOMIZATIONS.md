# Fish Shell Customizations (Hydro + Dracula)

This document captures the current “known good” Fish setup in this repo and how to restore/adjust it.

## Prompt: Hydro (via Fisher)

This repo tracks your Fisher plugin list in `~/.config/fish/fish_plugins`.

To install/update plugins (including Hydro):

```bash
fisher update
```

Repo shortcut (recommended):

```bash
./scripts/bootstrap_fish_plugins.sh
```

If `fisher` is not installed yet (fresh machine / disaster recovery), bootstrap it first:

```bash
curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source
fisher install jorgebucaran/fisher
fisher update
```

Or install Hydro explicitly:

```bash
fisher install jorgebucaran/hydro
```

### Prompt conflict notes

Hydro defines `fish_prompt` and (depending on your configuration) may also define `fish_right_prompt`.
To avoid conflicts, any prior custom prompt implementations are kept as backups:

- `~/.config/fish/functions/fish_prompt.fish.backup`
- `~/.config/fish/functions/fish_right_prompt.fish.backup`

If you want to restore your old prompt temporarily, rename the backups back to `fish_prompt.fish` / `fish_right_prompt.fish`
and reload your shell.

**Note on `$$var` in Fish**: Hydro’s `fish_prompt.fish` uses `$$var` for *indirect expansion* (it dereferences a variable whose name is stored in another variable). In Fish, the shell PID is exposed as `$fish_pid` (not `$$`).

## Theme: Dracula (cohesive dark theme)

- **Fish syntax highlighting**: set in `~/.config/fish/config.fish` using a Dracula palette (we intentionally do **not** track `fish_variables` to avoid noisy diffs).
- **fzf**: `FZF_DEFAULT_OPTS` gets a Dracula-style color scheme by default (only if you haven’t set it already).
- **bat**: `BAT_THEME` defaults to `Dracula` (only if you haven’t set it already).

To preview/change Fish themes interactively:

```bash
fish_config theme
```

## Greeting Function

A rotating greeting function lives at:
`~/.config/fish/functions/fish_greeting.fish`

To customize:

```bash
cursor --wait ~/.config/fish/functions/fish_greeting.fish
```

## Verifying Configuration

After making changes, reload Fish:

```bash
exec fish
```
