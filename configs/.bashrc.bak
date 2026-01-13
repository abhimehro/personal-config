# ============================================
# Bash Shell Configuration
# ============================================
# Ported from Fish config with Warp compatibility
# This config prioritizes stability and mirrors your Fish setup

# Exit early for non-interactive shells (faster for scripts)
[[ $- != *i* ]] && return

# ============================================
# Homebrew PATH (Apple Silicon)
# ============================================
export PATH="/opt/homebrew/bin:$PATH"
export PATH="$HOME/bin:$PATH"
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/.cache/lm-studio/bin:$PATH"

# ============================================
# Environment Variables
# ============================================
# Network Mode Manager - Control D and Windscribe integration
export NM_ROOT="$HOME/Documents/dev/personal-config"

# Set default editor - NeoVim
if [ -z "$EDITOR" ]; then
    export EDITOR="nvim"
fi

# ============================================
# Modern CLI Tool Aliases
# ============================================
# Better ls with eza
if command -v eza &> /dev/null; then
    alias ls='eza --icons'
    alias ll='eza -lah --icons'
    alias la='eza -a --icons'
    alias tree='eza --tree --icons'
fi

# Better cat with bat
if command -v bat &> /dev/null; then
    alias cat='bat --style=plain'
    alias bathelp='bat --style=full'
fi

# Better find with fd
if command -v fd &> /dev/null; then
    alias find='fd'
fi

# Better grep with ripgrep
if command -v rg &> /dev/null; then
    alias grep='rg'
fi

# ============================================
# Quick Navigation Aliases
# ============================================
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'

alias dev='cd ~/Documents/dev'
alias config='cd ~/Documents/dev/personal-config'
alias downloads='cd ~/Downloads'
alias desktop='cd ~/Desktop'

# ============================================
# Git Shortcuts
# ============================================
alias gs='git status'
alias ga='git add'
alias gaa='git add --all'
alias gc='git commit'
alias gcm='git commit -m'
alias gp='git push'
alias gpl='git pull'
alias gl='git log --oneline --graph'
alias gd='git diff'
alias gb='git branch'
alias gco='git checkout'

# ============================================
# Safe Operations
# ============================================
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

# ============================================
# Colorize Commands
# ============================================
# macOS ships BSD grep/diff; Homebrew installs GNU variants as ggrep/gdiff
if ! command -v rg &> /dev/null && command -v ggrep &> /dev/null; then
    alias grep='ggrep --color=auto'
fi

if command -v gdiff &> /dev/null; then
    alias diff='gdiff --color=auto'
fi

# ============================================
# Utility Aliases
# ============================================
alias bashconfig='$EDITOR ~/.config/bash/.bashrc'
alias bashedit='$EDITOR ~/.config/bash/.bashrc'
alias reload='source ~/.config/bash/.bashrc'

# ============================================
# History Configuration
# ============================================
HISTFILE=~/.bash_history
HISTSIZE=10000
HISTFILESIZE=10000
export HISTCONTROL=ignoredups:ignorespace
shopt -s histappend

# ============================================
# Theme (Dracula) - Color definitions for prompt
# ============================================
# Define Dracula colors for use in custom prompts
declare -r DRACULA_BG="#282a36"
declare -r DRACULA_FG="#f8f8f2"
declare -r DRACULA_COMMENT="#6272a4"
declare -r DRACULA_CYAN="#8be9fd"
declare -r DRACULA_GREEN="#50fa7b"
declare -r DRACULA_ORANGE="#ffb86c"
declare -r DRACULA_PINK="#ff79c6"
declare -r DRACULA_PURPLE="#bd93f9"
declare -r DRACULA_RED="#ff5555"
declare -r DRACULA_YELLOW="#f1fa8c"

# Tool theming defaults
if [ -z "$BAT_THEME" ]; then
    export BAT_THEME="Dracula"
fi

if [ -z "$FZF_DEFAULT_OPTS" ]; then
    export FZF_DEFAULT_OPTS="--color=bg+:#44475a,bg:#282a36,spinner:#f8f8f2,hl:#6272a4,fg:#f8f8f2,header:#6272a4,info:#bd93f9,pointer:#ff79c6,marker:#ff79c6,fg+:#f8f8f2,prompt:#bd93f9,hl+:#ff79c6"
fi

# ============================================
# Custom Functions
# ============================================

# Create a directory and cd into it
mkcd() {
    if [ $# -lt 1 ]; then
        echo "Usage: mkcd <dir>" >&2
        return 2
    fi
    mkdir -p "$1" && cd "$1"
}

# Show PATH in readable format
path() {
    echo "$PATH" | tr ':' '\n'
}

# Extract various archive formats
extract() {
    if [ $# -lt 1 ]; then
        echo "Usage: extract <archive>" >&2
        return 2
    fi

    local file="$1"
    if [ ! -f "$file" ]; then
        echo "'$file' is not a valid file" >&2
        return 1
    fi

    case "$file" in
        *.tar.bz2|*.tbz2) tar xjf "$file" ;;
        *.tar.gz|*.tgz)   tar xzf "$file" ;;
        *.tar)            tar xf "$file" ;;
        *.bz2)            bunzip2 "$file" ;;
        *.gz)             gunzip "$file" ;;
        *.rar)            unrar x "$file" ;;
        *.zip)            unzip "$file" ;;
        *.Z)              uncompress "$file" ;;
        *.7z)             7z x "$file" ;;
        *)
            echo "'$file' cannot be extracted via extract()" >&2
            return 3
            ;;
    esac
}

# Quick backup function
backup() {
    if [ $# -lt 1 ]; then
        echo "Usage: backup <file>" >&2
        return 2
    fi

    local src="$1"
    if [ ! -e "$src" ]; then
        echo "'$src' does not exist" >&2
        return 1
    fi

    local dst="${src}.backup.$(date +%Y%m%d_%H%M%S)"
    cp -p "$src" "$dst"
}

# ============================================
# Heavy Integrations (Conditional for Warp)
# ============================================
# These are gated behind interactive shell checks
# to avoid delays in non-interactive contexts (e.g., scripts, Warp startup)

# Conda initialization (optional - skip if causes delays)
if [ -f /opt/anaconda3/bin/conda ]; then
    __conda_setup="$(/opt/anaconda3/bin/conda shell.bash hook 2> /dev/null)"
    if [ $? -eq 0 ]; then
        eval "$__conda_setup"
    elif [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/opt/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/opt/anaconda3/bin:$PATH"
    fi
    unset __conda_setup
fi

# Chruby (Ruby version manager) - sourced from Homebrew
if [ -f /opt/homebrew/opt/chruby/share/chruby/chruby.sh ]; then
    source /opt/homebrew/opt/chruby/share/chruby/chruby.sh
    source /opt/homebrew/opt/chruby/share/chruby/auto.sh
    
    # Set default Ruby version if it exists
    if [ -d "$HOME/.rubies/ruby-3.4.7" ]; then
        chruby ruby-3.4.7 2>/dev/null
    fi
fi

# Zoxide (smarter cd) - optional, can be disabled if problematic
if command -v zoxide &> /dev/null; then
    eval "$(zoxide init bash)"
fi

# ============================================
# Bash Settings
# ============================================
# Append to history instead of overwriting
shopt -s histappend

# Check window size after each command
shopt -s checkwinsize

# Case-insensitive globbing
shopt -s nocaseglob

# ============================================
# Key Bindings
# ============================================
# Use Emacs key bindings (default in Bash)
set -o emacs

# Optional: Uncomment for Vi key bindings
# set -o vi

# ============================================
# FNM (Fast Node Manager)
# ============================================
if command -v fnm &> /dev/null; then
    eval "$(fnm env --use-on-cd)"
fi

# Warpify Subshells
printf '\eP$f{"hook": "SourcedRcFileForWarp", "value": { "shell": "bash"}}\x9c'
