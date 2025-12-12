# ============================================
# Fish Shell Configuration
# ============================================

# ============================================
# Homebrew PATH
# ============================================
# For Apple Silicon (M1/M2/M3)
fish_add_path /opt/homebrew/bin

# ============================================
# Conda Initialize
# ============================================
# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
if test -f /opt/anaconda3/bin/conda
    eval /opt/anaconda3/bin/conda \"shell.fish\" \"hook\" $argv | source
else
    if test -f \"/opt/anaconda3/etc/fish/conf.d/conda.fish\"
        . \"/opt/anaconda3/etc/fish/conf.d/conda.fish\"
    else
        set -x PATH \"/opt/anaconda3/bin\" $PATH
    end
end
# <<< conda initialize <<<

# ============================================
# Additional PATH entries
# ============================================
# LM Studio CLI
set -gx PATH $PATH /Users/abhimehrotra/.cache/lm-studio/bin

# Local bin
set -gx PATH $PATH $HOME/.local/bin

# ============================================
# Environment Variables
# ============================================
# Network Mode Manager - Control D and Windscribe integration
set -gx NM_ROOT $HOME/Documents/dev/personal-config

# Set default editor - using nano as fallback (change to: vim, code, cursor, etc.)
set -Ux EDITOR nano

# ============================================
# Modern CLI Tool Aliases
# ============================================
# Better ls with eza
if type -q eza
    alias ls='eza --icons'
    alias ll='eza -lah --icons'
    alias la='eza -a --icons'
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
alias grep='grep --color=auto'
alias diff='diff --color=auto'

# ============================================
# Utility Aliases
# ============================================
# Quick file editing
alias fishconfig='$EDITOR ~/.config/fish/config.fish'
alias fishedit='$EDITOR ~/.config/fish/config.fish'

# Reload fish config
alias reload='source ~/.config/fish/config.fish'

# Show PATH in readable format
alias path='echo $PATH | tr \" \" \"\n\"'

# ============================================
# Hydro Prompt Customization
# ============================================
set -g hydro_color_pwd blue
set -g hydro_color_git yellow
set -g hydro_color_error red
set -g hydro_color_prompt green
set -g hydro_color_duration cyan

# ============================================
# History Configuration
# ============================================
set -g fish_history_limit 10000

# ============================================
# Fish Theme Configuration
# ============================================
# To set ayu-mirage theme, run: fish_config theme choose \"ayu Mirage\"
# Or install via: fisher install ayu-theme/fish-ayu
# Then set: set -U fish_theme ayu-mirage
#
# Note: Themes are typically managed via fish_config command or fisher plugins.
# Run 'fish_config' to open the theme selector GUI, or install themes via fisher.

# ============================================
# Custom Functions
# ============================================
# Create a directory and cd into it
function mkcd
    mkdir -p $argv[1]; and cd $argv[1]
end

# Extract various archive formats
function extract
    if test -f $argv[1]
        switch $argv[1]
            case '*.tar.bz2'
                tar xjf $argv[1]
            case '*.tar.gz'
                tar xzf $argv[1]
            case '*.bz2'
                bunzip2 $argv[1]
            case '*.rar'
                unrar x $argv[1]
            case '*.gz'
                gunzip $argv[1]
            case '*.tar'
                tar xf $argv[1]
            case '*.tbz2'
                tar xjf $argv[1]
            case '*.tgz'
                tar xzf $argv[1]
            case '*.zip'
                unzip $argv[1]
            case '*.Z'
                uncompress $argv[1]
            case '*.7z'
                7z x $argv[1]
            case '*'
                echo \"'$argv[1]' cannot be extracted via extract()\"
        end
    else
        echo \"'$argv[1]' is not a valid file\"
    end
end

# Quick backup function
function backup
    cp $argv[1] $argv[1].backup.(date +%Y%m%d_%H%M%S)
end

# ============================================
# Welcome Message (optional - comment out if you don't want it)
# ============================================
# if status is-interactive
#     echo \"🐟 Fish shell loaded! Type 'fishconfig' to edit config.\"
# end
