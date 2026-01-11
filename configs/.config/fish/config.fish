# ============================================
# Fish Shell Configuration
# ============================================

# ============================================
# Homebrew PATH
# ============================================
# For Apple Silicon (M1/M2/M3)
fish_add_path --global --prepend /opt/homebrew/bin

# User/local bins (kept global to avoid rewriting universal vars on every shell)
fish_add_path --global --prepend $HOME/bin
fish_add_path --global --prepend $HOME/.local/bin

# LM Studio CLI (append to avoid shadowing system tools)
fish_add_path --global --append $HOME/.cache/lm-studio/bin

# ============================================
# Conda Initialize
# ============================================
# Moved to `init_conda` function (lazy-loaded).
# Run `init_conda` to activate conda environment.

# ============================================
# Ruby Version Manager (chruby-fish)
# ============================================
# Ported from Zsh: provides automatic Ruby version switching
# Install: brew install chruby-fish
if status is-interactive
    if test -f /opt/homebrew/opt/chruby-fish/share/chruby/chruby.fish
        source /opt/homebrew/opt/chruby-fish/share/chruby/chruby.fish
    end

    if test -f /opt/homebrew/opt/chruby-fish/share/chruby/auto.fish
        source /opt/homebrew/opt/chruby-fish/share/chruby/auto.fish
    end

    # Set default Ruby version (if chruby is available and ruby exists)
    if type -q chruby; and test -d ~/.rubies/ruby-3.4.7
        chruby ruby-3.4.7
    end
end

# ============================================
# Node Version Manager (fnm)
# ============================================
if status is-interactive
    if type -q fnm
        fnm env --use-on-cd | source
    end
end

# ============================================
# Zoxide (smarter cd)
# ============================================
# Better alternative to z/autojump - installed via brew install zoxide
if type -q zoxide
    zoxide init fish | source
end

# ============================================
# Environment Variables
# ============================================
# Network Mode Manager - Control D and Windscribe integration
set -gx NM_ROOT $HOME/Documents/dev/personal-config

# Set default editor - NeoVim
# Note: NeoVim blocks by default when used as EDITOR, perfect for tools like `git commit`.
# Avoid setting universal variables on every startup; keep this as a safe fallback.
if not set -q EDITOR
    set -gx EDITOR "nvim"
end

# ============================================
# Modern CLI Tool Aliases
# ============================================
# Better ls with eza
if type -q eza
    alias ls='eza --icons --group-directories-first'
    alias ll='eza -lah --icons --group-directories-first'
    alias la='eza -a --icons --group-directories-first'
    alias tree='eza --tree --icons'
end

# Better cat with bat
if type -q bat
    alias cat='bat --style=plain'
    alias bathelp='bat --style=full'
end

# Better find with fd
if type -q fd
    alias find='fd'
end

# Better grep with ripgrep
if type -q rg
    alias grep='rg'
end

# Note: tlrc package provides 'tldr' command (not 'tlrc')
# The command is already available as 'tldr'

# ============================================
# Quick Navigation Aliases
# ============================================
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'

# Quick access to common directories
alias dev='cd ~/Documents/dev'
alias config='cd ~/Documents/dev/personal-config'
alias downloads='cd ~/Downloads'
alias desktop='cd ~/Desktop'

# ============================================
# Abbreviations (expand in place)
# ============================================

# Git
abbr --add gs  git status
abbr --add ga  git add
abbr --add gaa git add --all
abbr --add gc  git commit
abbr --add gcm git commit -m
abbr --add gp  git push
abbr --add gpl git pull
abbr --add gl  git log --oneline --graph
abbr --add gd  git diff
abbr --add gb  git branch
abbr --add gco git checkout

# SSH Abbreviations (Cursor IDE)
abbr --add scv ssh cursor-vpn
abbr --add scl ssh cursor-local
abbr --add scm ssh cursor-mdns
abbr --add sca ssh cursor-auto

# ============================================
# Safe Operations
# ============================================
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

# ============================================
# Colorize Commands
# ============================================
# macOS ships BSD grep/diff; Homebrew installs GNU variants as ggrep/gdiff.
if not type -q rg; and type -q ggrep
    alias grep='ggrep --color=auto'
end
if type -q gdiff
    alias diff='gdiff --color=auto'
end

# ============================================
# Utility Aliases
# ============================================
# Quick file editing
function __run_editor --description 'Run $EDITOR (supports args like "nvim" or "code --wait")'
    set -l editor (string split ' ' -- $EDITOR)
    command $editor $argv
end

alias fishconfig='__run_editor ~/.config/fish/config.fish'
alias fishedit='__run_editor ~/.config/fish/config.fish'

# Reload fish config
alias reload='source ~/.config/fish/config.fish'

# ============================================
# Hydro Prompt Customization
# ============================================
# Hydro provides fish_prompt / fish_right_prompt (installed via Fisher: `jorgebucaran/hydro`).
# Keep any custom prompts renamed (see `fish_prompt.fish.backup` / `fish_right_prompt.fish.backup`)
# so Hydro can take precedence.
set -g hydro_color_pwd bd93f9
set -g hydro_color_git f1fa8c
set -g hydro_color_error ff5555
set -g hydro_color_prompt 50fa7b
set -g hydro_color_duration 6272a4

# ============================================
# History Configuration
# ============================================
set -g fish_history_limit 10000

# ============================================
# Theme (Dracula)
# ============================================
# Option A: keep the repo clean by NOT tracking `fish_variables` (it is machine-local and changes often).
# Instead, we set a stable Dracula palette here so a fresh restore looks the same.
if status is-interactive
    # Fish syntax highlighting (Dracula)
    set -g fish_color_normal f8f8f2
    set -g fish_color_command 8be9fd
    set -g fish_color_param bd93f9
    set -g fish_color_quote f1fa8c
    set -g fish_color_redirection f8f8f2
    set -g fish_color_end ffb86c
    set -g fish_color_error ff5555
    set -g fish_color_comment 6272a4
    set -g fish_color_operator 50fa7b
    set -g fish_color_escape ff79c6
    set -g fish_color_autosuggestion 6272a4
    set -g fish_color_host bd93f9
    set -g fish_color_host_remote bd93f9
    set -g fish_color_user 8be9fd
    set -g fish_color_cancel ff5555 --reverse
    set -g fish_color_search_match --bold --background=44475a
    set -g fish_color_selection --bold --background=44475a
    set -g fish_color_valid_path --underline=single

    # Pager (Dracula-ish)
    set -g fish_pager_color_completion f8f8f2
    set -g fish_pager_color_description 6272a4
    set -g fish_pager_color_prefix 8be9fd
    set -g fish_pager_color_progress 6272a4
    set -g fish_pager_color_selected_background --background=44475a
    set -g fish_pager_color_selected_completion f8f8f2
    set -g fish_pager_color_selected_description 6272a4
    set -g fish_pager_color_selected_prefix 8be9fd
end

# Tool theming defaults (only if you haven’t set them already)
if not set -q BAT_THEME
    set -gx BAT_THEME "Dracula"
end

if not set -q FZF_DEFAULT_OPTS
    set -gx FZF_DEFAULT_OPTS "--color=bg+:#44475a,bg:#282a36,spinner:#f8f8f2,hl:#6272a4,fg:#f8f8f2,header:#6272a4,info:#bd93f9,pointer:#ff79c6,marker:#ff79c6,fg+:#f8f8f2,prompt:#bd93f9,hl+:#ff79c6"
end

# ============================================
# Custom Functions
# ============================================
# Functions have been moved to ~/.config/fish/functions/ for lazy-loading:
# - mkcd
# - showpath
# - extract (supports .xz now)
# - backup

# ============================================
# Welcome Message (optional - comment out if you don't want it)
# ============================================
# if status is-interactive
#     echo \"🐟 Fish shell loaded! Type 'fishconfig' to edit config.\"
# end

