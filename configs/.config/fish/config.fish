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
# Conda Initialize (interactive-only for faster non-interactive shells)
# ============================================
if status is-interactive
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
end

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
# Create a directory and cd into it
function mkcd
    if test (count $argv) -lt 1
        echo "Usage: mkcd <dir>" >&2
        return 2
    end

    mkdir -p -- $argv[1]; and cd -- $argv[1]
end

# Show PATH in readable format
function path
    # $PATH is a list in fish; print one per line for readability.
    printf '%s\n' $PATH
end

# Extract various archive formats
function extract
    if test (count $argv) -lt 1
        echo "Usage: extract <archive>" >&2
        return 2
    end

    set -l file_raw $argv[1]
    if not test -f "$file_raw"
        echo "'$file_raw' is not a valid file" >&2
        return 1
    end

    # Prevent option-injection when files start with '-' by forcing a path.
    # This guards against treating a user-supplied filename as flags.
    set -l file $file_raw
    if string match -qr '^-' -- $file_raw
        set file "./$file_raw"
    end

    switch $file_raw
        case '*.tar.bz2' '*.tbz2'
            command tar xjf $file
        case '*.tar.gz' '*.tgz'
            command tar xzf $file
        case '*.tar'
            command tar xf $file
        case '*.bz2'
            command bunzip2 $file
        case '*.gz'
            command gunzip $file
        case '*.rar'
            command unrar x $file
        case '*.zip'
            command unzip $file
        case '*.Z'
            command uncompress $file
        case '*.7z'
            command 7z x $file
        case '*'
            echo "'$file_raw' cannot be extracted via extract()" >&2
            return 3
    end
end

# Quick backup function
function backup
    if test (count $argv) -lt 1
        echo "Usage: backup <file>" >&2
        return 2
    end

    set -l src_raw $argv[1]
    if not test -e "$src_raw"
        echo "'$src_raw' does not exist" >&2
        return 1
    end

    set -l src $src_raw
    set -l dst "$src_raw".backup.(date +%Y%m%d_%H%M%S)

    # Prevent option-injection when filenames start with '-'.
    if string match -qr '^-' -- $src_raw
        set src "./$src_raw"
        set dst "./$dst"
    end

    command cp -p $src $dst
end

# ============================================
# Welcome Message (optional - comment out if you don't want it)
# ============================================
# if status is-interactive
#     echo \"🐟 Fish shell loaded! Type 'fishconfig' to edit config.\"
# end

# Mole shell completion
set -l output (mole completion fish 2>/dev/null); and echo "$output" | source
