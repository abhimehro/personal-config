# ============================================
# Fish Shell Configuration
# ============================================

# ============================================
# Path Management
# ============================================
if not set -q __fish_path_initialized
    # Homebrew (Apple Silicon)
    fish_add_path --global --prepend /opt/homebrew/bin /opt/homebrew/sbin

    # User binaries (prepend to prioritize local overrides)
    fish_add_path --global --prepend $HOME/bin $HOME/.local/bin

    # Tool-specific bins (append to avoid shadowing system tools)
    fish_add_path --global --append $HOME/.cache/lm-studio/bin

    set -g __fish_path_initialized 1
end

# ============================================
# Theme and Prompt Management
# ============================================
# Tide prompt styling is managed by universal variables.
# Fish syntax colors use the Dracula Official theme.
# A helper re-applies the Fish theme only if another plugin resets it.
# See: ~/dev/personal-config/configs/.config/fish/RESTORE_CUSTOMIZATIONS.md

# ============================================
# Version Control (Git)
# ============================================
# Prefer delta for Git output in Fish sessions when it is installed.
# We set GIT_PAGER for this shell instead of running `git config --global`
# during startup, which avoids lock-file races when multiple shells start.
if type -q delta
    set -gx GIT_PAGER delta
end

# ============================================
# Tool Initialization
# ============================================
if status is-interactive
    __ensure_dracula_theme

    # --- Ruby (chruby-fish) ---
    if test -d /opt/homebrew/opt/chruby-fish/share/chruby
        source /opt/homebrew/opt/chruby-fish/share/chruby/chruby.fish
        source /opt/homebrew/opt/chruby-fish/share/chruby/auto.fish

        # Default Ruby fallback only when the current directory does not pin one.
        if type -q chruby; and test -d ~/.rubies/ruby-3.4.7
            if not test -f .ruby-version
                chruby ruby-3.4.7
            end
        end
    end

    # --- Node (fnm) ---
    # Stderr is redirected to /dev/null to suppress fnm's INFO-level version file
    # scan messages, which fire before FNM_LOGLEVEL takes effect in the environment.
    if type -q fnm
        fnm env --use-on-cd 2>/dev/null | source
    end

    # --- Zoxide (Navigation) ---
    if type -q zoxide
        zoxide init fish | source
    end
end

# ============================================
# SSH Agent Health Check
# ============================================
# Prefer the 1Password SSH agent when available, and fall back to the
# macOS agent when its socket is not present.
set -l op_sock "$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
if test -S $op_sock
    set -gx SSH_AUTH_SOCK $op_sock
else
    set -l mac_sock (command launchctl getenv SSH_AUTH_SOCK 2>/dev/null)
    if test -n "$mac_sock" -a -S "$mac_sock"
        set -gx SSH_AUTH_SOCK $mac_sock
    end
end

# ============================================
# Environment Variables
# ============================================
set -gx NM_ROOT $HOME/dev/personal-config

# Homebrew
set -gx HOMEBREW_NO_REQUIRE_TAP_TRUST 1
set -gx HOMEBREW_NO_ENV_HINTS 1

set -q EDITOR; or set -gx EDITOR nvim
set -q BAT_THEME; or set -gx BAT_THEME Dracula

if not set -q FZF_DEFAULT_OPTS
    set -gx FZF_DEFAULT_OPTS "--style=full --color=bg+:#44475a,bg:#282a36,spinner:#f8f8f2,hl:#6272a4,fg:#f8f8f2,header:#6272a4,info:#bd93f9,pointer:#ff79c6,marker:#ff79c6,fg+:#f8f8f2,prompt:#bd93f9,hl+:#ff79c6"
end

# Make FZF use fd so it respects .gitignore-like traversal expectations and skips .git.
if type -q fd
    set -gx FZF_DEFAULT_COMMAND 'fd --type f --hidden --exclude .git'
    set -gx FZF_CTRL_T_COMMAND $FZF_DEFAULT_COMMAND
end

# ============================================
# Custom Functions
# ============================================
# Custom functions are autoloaded from ~/.config/fish/functions.

# ============================================
# Aliases
# ============================================

# Navigation
alias ..        'cd ..'
alias ...       'cd ../..'
alias ....      'cd ../../..'
alias .....     'cd ../../../..'
alias dev       'cd ~/dev'
alias config    'cd ~/dev/personal-config'
alias downloads 'cd ~/Downloads'
alias desktop   'cd ~/Desktop'

# Modern replacements
if type -q eza
    alias ls   'eza --icons --group-directories-first'
    alias ll   'eza -lah --icons --group-directories-first'
    alias la   'eza -a --icons --group-directories-first'
    alias tree 'eza --tree --icons'
end

if type -q bat
    alias cat     'bat --style=plain'
    alias bathelp 'bat --style=full'
end

type -q fd; and alias find 'fd'
type -q rg; and alias grep 'rg'

# Safety
abbr -a rm 'rm -i'
abbr -a cp 'cp -i'
abbr -a mv 'mv -i'

# Color support fallbacks (BSD vs GNU)
if not type -q rg; and type -q ggrep
    alias grep 'ggrep --color=auto'
end
if type -q gdiff
    alias diff 'gdiff --color=auto'
end

alias fishconfig '__run_editor ~/.config/fish/config.fish'
alias fishedit   '__run_editor ~/.config/fish/config.fish'
alias reload     'source ~/.config/fish/config.fish'

# ============================================
# Abbreviations
# ============================================

# Git
abbr -a gs  git status
abbr -a ga  git add
abbr -a gaa git add --all
abbr -a gc  git commit
abbr -a gcm git commit -m
abbr -a gp  git push
abbr -a gpl git pull
abbr -a gl  git log --oneline --graph
abbr -a gd  git diff
abbr -a gb  git branch
abbr -a gco git checkout
abbr -a gmc git-mirror-clean

# Cursor IDE (SSH)
abbr -a scv ssh cursor-vpn
abbr -a scl ssh cursor-local
abbr -a scm ssh cursor-mdns
abbr -a sca ssh cursor-auto

# Network Mode Manager
abbr -a nms  nm-status
abbr -a nmb  nm-browse
abbr -a nmp  nm-privacy
abbr -a nmg  nm-gaming
abbr -a nmv  nm-vpn
abbr -a nmvp nm-vpn privacy
abbr -a nmvg nm-vpn gaming
abbr -a nmvb nm-vpn browsing
abbr -a nmr  nm-regress
abbr -a nmcs nm-cd-status

# ============================================
# Media Pipeline - Alldebrid Download Phase (NEW)
# ============================================
# These commands manage downloading files from Alldebrid into the media pipeline.
# The NEW pre-download approval system uses candidate files for safety.
# Usage: alldebrid-sync -> approve-download -> files appear in approval_needed/

abbr -a alldebrid-sync       "$NM_ROOT/media-streaming/scripts/sync-alldebrid.sh"
abbr -a alldebrid-sync-dry   "$NM_ROOT/media-streaming/scripts/sync-alldebrid.sh --dry-run"
abbr -a ad-approve           "$NM_ROOT/media-streaming/scripts/approve-download"
abbr -a ad-list              "$NM_ROOT/media-streaming/scripts/approve-download --list"
abbr -a ad-status            "$NM_ROOT/media-streaming/scripts/approve-download --status"
abbr -a ad-fetch             "$NM_ROOT/media-streaming/scripts/approve-download --fetch"

# ============================================
# Media Pipeline - Processing Phase
# ============================================
# These commands process files after they've been downloaded.

# Mount and server management
alias mmount    "$NM_ROOT/media-streaming/scripts/mount-media.sh"
alias mserver   "$NM_ROOT/media-streaming/scripts/media-server-daemon.sh"
alias finalize "$NM_ROOT/media-streaming/scripts/final-media-server.sh"

# File processing and renaming
alias rename-media "$NM_ROOT/media-streaming/scripts/rename-media.sh"
abbr -a rm-approve   "$NM_ROOT/media-streaming/scripts/rename-media.sh --approve-ready"
abbr -a rm-pending   "$NM_ROOT/media-streaming/scripts/rename-media.sh --list-pending"

# WebDAV rotation
abbr -a rotate-webdav "$NM_ROOT/media-streaming/scripts/rotate-media-webdav.sh"

# ============================================
# Media Pipeline - Setup
# ============================================
alias setup-gdrive "$NM_ROOT/media-streaming/scripts/setup-gdrive.sh"
alias setup-media  "$NM_ROOT/media-streaming/scripts/setup-media-library.sh"

# ============================================
# Media Pipeline - Legacy (Deprecated)
# ============================================
# OLD post-download approval system: moves files from approval_needed/ to permute_input/
# NOTE: This is the LEGACY system for manual Permute 4 HEVC conversion.
#       The NEW system (approve-download) handles pre-download approval.
#       Keep this for backwards compatibility if needed.
alias approve-downloads "$NM_ROOT/media-streaming/scripts/approve-downloads.sh"
abbr -a list-downloads "$NM_ROOT/media-streaming/scripts/approve-downloads.sh --list"

# ============================================
# Media Pipeline - Utility
# ============================================
# Check stale mounts
alias check-stale "$NM_ROOT/media-streaming/scripts/check-stale-mounts.sh"

# Sync LaunchAgents for media services
alias sync-media-agents "$NM_ROOT/media-streaming/scripts/sync-launchagents.sh"

# Bulk rename files in cloud storage
alias bulk-rename "$NM_ROOT/media-streaming/scripts/bulk-rename-cloud.sh"

# Media status and restart functions (defined in functions/media-*.fish)
# Usage: media-status, media-restart, media-logs

# History Setup
set -g fish_history_limit 10000
set -U fish_user_paths $fish_user_paths /Users/speedybee/.local/bin
fish_add_path /Users/speedybee/scripts

# Added by Antigravity IDE
fish_add_path /Users/speedybee/.antigravity-ide/antigravity-ide/bin
