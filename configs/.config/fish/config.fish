# ============================================
# Fish Shell Configuration
# ============================================

# ============================================
# Path Management
# ============================================
# Homebrew (Apple Silicon)
fish_add_path --global --prepend /opt/homebrew/bin /opt/homebrew/sbin

# User binaries (Prepend to prioritize local overrides)
fish_add_path --global --prepend $HOME/bin $HOME/.local/bin

# Tool-specific bins (Append to avoid shadowing system tools)
fish_add_path --global --append $HOME/.cache/lm-studio/bin

# ============================================
# Tool Initialization
# ============================================

# Interactive-only initializations
if status is-interactive

    # --- Ruby (chruby-fish) ---
    if test -d /opt/homebrew/opt/chruby-fish/share/chruby
        source /opt/homebrew/opt/chruby-fish/share/chruby/chruby.fish
        source /opt/homebrew/opt/chruby-fish/share/chruby/auto.fish

        # Default Ruby fallback
        if type -q chruby; and test -d ~/.rubies/ruby-3.4.7
            chruby ruby-3.4.7
        end
    end

    # --- Node (fnm) ---
    if type -q fnm
        fnm env --use-on-cd | source
    end

    # --- Zoxide (Navigation) ---
    if type -q zoxide
        zoxide init fish | source
    end

    # --- Mole (Tunneling) ---
    if type -q mole
        mole completion fish 2>/dev/null | source
    end

end

# Note: Conda is initialized via 'init_conda' (lazy-loaded function).

# ============================================
# Environment Variables
# ============================================
set -gx NM_ROOT $HOME/Documents/dev/personal-config

# Default Editor (NeoVim)
# Kept as a safe fallback; avoid universal variable persistence issues.
if not set -q EDITOR
    set -gx EDITOR nvim
end

# Tool Theming Defaults
if not set -q BAT_THEME
    set -gx BAT_THEME Dracula
end

if not set -q FZF_DEFAULT_OPTS
    # Dracula FZF colors
    set -gx FZF_DEFAULT_OPTS "--color=bg+:#44475a,bg:#282a36,spinner:#f8f8f2,hl:#6272a4,fg:#f8f8f2,header:#6272a4,info:#bd93f9,pointer:#ff79c6,marker:#ff79c6,fg+:#f8f8f2,prompt:#bd93f9,hl+:#ff79c6"
end

# ============================================
# Aliases
# ============================================

# Navigation
alias ..    'cd ..'
alias ...   'cd ../..'
alias ....  'cd ../../..'
alias ..... 'cd ../../../..'

alias dev       'cd ~/Documents/dev'
alias config    'cd ~/Documents/dev/personal-config'
alias downloads 'cd ~/Downloads'
alias desktop   'cd ~/Desktop'

# Modern Replacements
if type -q eza
    alias ls    'eza --icons --group-directories-first'
    alias ll    'eza -lah --icons --group-directories-first'
    alias la    'eza -a --icons --group-directories-first'
    alias tree  'eza --tree --icons'
end

if type -q bat
    alias cat       'bat --style=plain'
    alias bathelp   'bat --style=full'
end

type -q fd; and alias find 'fd'
type -q rg; and alias grep 'rg'

# Safety
alias rm 'rm -i'
alias cp 'cp -i'
alias mv 'mv -i'

# Color Support Fallbacks (BSD vs GNU)
if not type -q rg; and type -q ggrep
    alias grep 'ggrep --color=auto'
end
if type -q gdiff
    alias diff 'gdiff --color=auto'
end

# Config Management
function __run_editor --description 'Run $EDITOR handling definition splitting'
    set -l editor (string split ' ' -- $EDITOR)
    command $editor $argv
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
abbr -a nmr  nm-regress
abbr -a nmcs nm-cd-status

# ============================================
# Visual Styling (Interactive)
# ============================================
if status is-interactive
    # Hydro Prompt Configuration
    set -g hydro_color_pwd      bd93f9
    set -g hydro_color_git      f1fa8c
    set -g hydro_color_error    ff5555
    set -g hydro_color_prompt   50fa7b
    set -g hydro_color_duration 6272a4

    # Fish Syntax Highlighting (Dracula)
    # Manual setting to ensure portability without relying on fish_variables
    set -g fish_color_normal            f8f8f2
    set -g fish_color_command           8be9fd
    set -g fish_color_param             bd93f9
    set -g fish_color_quote             f1fa8c
    set -g fish_color_redirection       f8f8f2
    set -g fish_color_end               ffb86c
    set -g fish_color_error             ff5555
    set -g fish_color_comment           6272a4
    set -g fish_color_operator          50fa7b
    set -g fish_color_escape            ff79c6
    set -g fish_color_autosuggestion    6272a4
    set -g fish_color_host              bd93f9
    set -g fish_color_host_remote       bd93f9
    set -g fish_color_user              8be9fd
    set -g fish_color_cancel            ff5555 --reverse
    set -g fish_color_search_match      --bold --background=44475a
    set -g fish_color_selection         --bold --background=44475a
    set -g fish_color_valid_path        --underline=single

    # Pager Colors
    set -g fish_pager_color_completion           f8f8f2
    set -g fish_pager_color_description          6272a4
    set -g fish_pager_color_prefix               8be9fd
    set -g fish_pager_color_progress             6272a4
    set -g fish_pager_color_selected_background  --background=44475a
    set -g fish_pager_color_selected_completion  f8f8f2
    set -g fish_pager_color_selected_description 6272a4
    set -g fish_pager_color_selected_prefix      8be9fd
end

# ============================================
# Greeting System (Time-Based)
# ============================================
if status is-interactive
    function fish_greeting
        # Get current hour (0-23)
        set -l hour (date +%H)

        # Morning greetings (5am - 12pm)
        set -l morning_greetings \
            "Namaste, bhai! Chal, aaj kuch solid code karte hain. ☀️" \
            "Greetings, fellow unit! Ready to convert caffeine into code? ☕" \
            "Good morning! Ready to debug the universe (or just our app) today? 🌌" \
            "Suprabhat, dost! Let's make today productive! 💻" \
            "Rise and shine! Ready to compile greatness? 🌅" \
            "Morning! Let's turn that coffee into commits. ☕→💻" \
            "Arre! Subah subah coding karne ka maza hi alag hai! 🚀" \
            "Hello World! Fresh start, fresh code. Let's do this! 🌍" \
            "Good morning! Time to make the magic happen. ✨"

        # Afternoon greetings (12pm - 6pm)
        set -l afternoon_greetings \
            "Arre, mere dost! Code karne ke liye taiyaar ho? 🚀" \
            "Kya haal hai, dost? Chalo, bug-fixing shuru karein! 🐛" \
            "SYN! Ready to ACK our way through some logic? 🧠" \
            "Hey! Ready to script a future where everything compiles on the first try? 🖖🏽" \
            "Handshake initiated. 👋 Ready to make the magic happen?" \
            "What's kickin', chicken? Ready to squash some bugs? 🐔" \
            "Afternoon, warrior! Let's ship some features. ⚓" \
            "Ready to ship it? 🛶 No looking back until the PR is merged!" \
            "Holla! 👋 Let's make this script look absolutely on fleek today." \
            "Greetings! Ready to do some adulting today? Let's crush these commits. ☕"

        # Evening/Night greetings (6pm - 5am)
        set -l evening_greetings \
            "Oye! Taiyaar ho world badalne ke liye? 💻🌙" \
            "Salutations! Shall we initiate a session of bug-free productivity? 👾" \
            "Yo! Ready to overclock our brains and ship some features? ⚓" \
            "01001000 01101001! Ready to push some commits? ⋈" \
            "Ahoy, matey! Ready to navigate the sea of syntax? 🦜" \
            "Let's compile 2026—one line at a time. 🔮 You in?" \
            "Ready to turn that software into hardware? Let's get to it! 🔩" \
            "Wassup, dawg? Ready to ship some code that's totally da bomb? 💣" \
            "Yo! Ready to get crunk on some logic? It's gonna be sick! 🤘" \
            "Cool beans! 🆒 Time to sit down and write some awesomesauce code." \
            "Late night grind! The best code happens after dark. 🌃" \
            "Evening vibes activated. Let's make some nocturnal magic. 🦇"

        # Select appropriate greeting set based on time
        set -l greetings  # Declare variable first
        if test $hour -ge 5 -a $hour -lt 12
            set greetings $morning_greetings
        else if test $hour -ge 12 -a $hour -lt 18
            set greetings $afternoon_greetings
        else
            set greetings $evening_greetings
        end

        # Pick random greeting from time-appropriate set
        set -l random_index (random 1 (count $greetings))
        echo -e "\n  $greetings[$random_index]\n"
    end
end

# History Setup
set -g fish_history_limit 10000
