# Restoring Fish Shell Customizations

This document helps restore customizations that may have been lost during migration.

## Theme: ayu-mirage

The ayu-mirage theme can be restored using one of these methods:

### Method 1: Using fish_config (GUI)
```bash
fish_config theme choose "ayu Mirage"
```

### Method 2: Using fisher plugin manager
```bash
# Install ayu theme plugin
fisher install ayu-theme/fish-ayu

# Set the theme
set -U fish_theme ayu-mirage
```

### Method 3: Manual installation
```bash
# Clone the theme repository
git clone https://github.com/ayu-theme/fish-ayu.git ~/.config/fish/themes/ayu

# Set the theme
set -U fish_theme ayu-mirage
```

## Greeting Function

A rotating greeting function has been created at:
`~/.config/fish/functions/fish_greeting.fish`

It includes greetings: "Hello!", "Namaste!", "Howdy!", "Hey there!", "Welcome back!"

To customize, edit the function file:
```bash
nano ~/.config/fish/functions/fish_greeting.fish
```

## Other Customizations

If you had other customizations that aren't showing up:

1. **Check fish_variables**: Universal variables are stored in `~/.config/fish/fish_variables`
   - These are automatically synced via the symlink
   - Run `fish -c "set -U --show"` to see all universal variables

2. **Check conf.d files**: Configuration snippets in `~/.config/fish/conf.d/`
   - These are automatically synced via the symlink

3. **Check functions**: Custom functions in `~/.config/fish/functions/`
   - These are automatically synced via the symlink

4. **Check completions**: Custom completions in `~/.config/fish/completions/`
   - These are automatically synced via the symlink

## Verifying Configuration

After making changes, reload fish shell:
```bash
exec fish
```

Or restart your terminal.
