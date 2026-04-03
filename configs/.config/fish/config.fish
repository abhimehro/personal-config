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
# Theme and Prompt Management
# ============================================
# NOTE: Prompt theming is managed by Tide via `set -U tide_*_color` universals, and syntax colors are managed by `fish_config theme choose "Dracula Official"` (also stored as universals). This keeps our config.fish clean and focused on functional setup rather than visual styling, which is handled separately through the interactive theme configuration. See: configs/.config/fish/RESTORE_CUSTOMIZATIONS.md for setup instructions on restoring your visual customizations after a fresh install.
# This approach allows you to easily switch themes and prompt styles using the interactive `fish_config` tool without needing to modify your config.fish, while still ensuring that your preferred colors and styles are preserved as universals that persist across sessions and installations. It also keeps the visual styling concerns separate from the functional setup of your shell environment, making it easier to manage and maintain over time.
# If you ever want to change your theme or prompt style, simply run `fish_config` and choose your desired options. Your selections will be saved as universals, so they will automatically apply in all future sessions without needing to edit your config.fish again. This way, you can focus on configuring the functional aspects of your shell environment in config.fish, while leaving the visual customizations to be managed interactively through the theme configuration tool.
# By keeping the visual styling separate from the functional setup, we also ensure that any changes to themes or prompt styles won't accidentally interfere with the core functionality of your shell environment, allowing for a more modular and maintainable configuration overall.
# In summary, the key point is that visual styling (themes and prompts) is managed interactively through `fish_config` and stored as universals, while config.fish focuses on setting up the functional environment (PATH, tool initialization, aliases, functions, etc.) without hardcoding visual preferences. This separation of concerns allows for greater flexibility and ease of maintenance in your shell configuration.
# This also means that if you ever want to share your config.fish with someone else, they can easily apply their own visual customizations through `fish_config` without needing to modify the shared config.fish, while still benefiting from the functional setup you've created. It's a win-win for both customization and maintainability!
# Overall, this approach allows you to have a clean and organized config.fish that focuses on the functional aspects of your shell environment, while still giving you the freedom to customize the visual styling through the interactive theme configuration tool without needing to edit your config.fish for visual changes. It's a great way to keep things modular and maintainable while still allowing for a personalized and visually appealing shell experience!

fish_config theme choose "Dracula Official"

# ============================================
# Version Control (Git)
# ============================================
# Set up Git to use the 'delta' pager for improved diffs if available
# This enhances the readability of git diffs in the terminal by providing syntax highlighting and better formatting, making it easier to review changes before committing or pushing code.
# By configuring Git to use 'delta' as the pager, you can quickly see the differences between file versions with color-coded output, which can help you catch mistakes and understand changes more effectively. If 'delta' is not installed, Git will fall back to the default pager, so this configuration is safe to include even if you don't have 'delta' installed yet.
# To install 'delta', you can typically use your package manager (e.g., `brew install git-delta` on macOS) and then this configuration will automatically take effect the next time you use Git commands that produce diff output (like `git diff`, `git show`, etc.). It's a great way to enhance your Git workflow with better visual feedback on code changes!
# If you ever want to customize the 'delta' output further, you can create a '.deltarc' configuration file in your home directory with additional settings for how 'delta' formats diffs, such as enabling side-by-side diffs, changing color schemes, or adjusting context lines. This allows you to tailor the diff output to your preferences and make it even more effective for reviewing code changes.
# Overall, setting up Git to use 'delta' as the pager is a simple yet powerful way to improve your code review process and make it easier to understand changes in your repositories, ultimately leading to better code quality and more efficient development workflows.
# Note: If you prefer to use 'delta' only for certain Git commands (like 'git diff') and not for others (like 'git log'), you can customize the Git configuration further by setting specific pager configurations for different commands. For example, you could set 'pager.diff' to 'delta' while leaving 'pager.log' as the default pager. This allows you to have more granular control over when 'delta' is used in your Git workflow, giving you the flexibility to choose the best tool for each type of output.
# To set 'delta' as the pager for all Git commands, you can use the following configuration:

git config --global core.pager delta

# If you want to set 'delta' as the pager only for specific commands, you can use:
# git config --global pager.diff delta
# git config --global pager.show delta 
# git config --global pager.log delta 
# This way, you can have 'delta' enhance the output of 'git diff', 'git show', and 'git log' while keeping the default pager for other Git commands that may not benefit from 'delta's formatting. It's all about customizing your Git experience to fit your workflow and preferences!
# By configuring Git to use 'delta' as the pager, you can significantly enhance the readability of your diffs and logs, making it easier to review changes and understand the history of your repositories. Whether you choose to use 'delta' for all Git commands or just specific ones, it's a great way to improve your Git workflow and make code reviews more efficient and enjoyable!
# In summary, setting up Git to use 'delta' as the pager is a powerful way to enhance your code review process by providing better formatting and syntax highlighting for diffs and logs. You can customize this configuration to fit your workflow, using 'delta' for all commands or just specific ones, and you can further tailor the output with a '.deltarc' file for an even more personalized experience. It's a simple change that can have a big impact on how you interact with Git and review code changes in your repositories!

# ============================================
# Language Runtimes (Managed by chruby-fish and fnm)
# ============================================
# NOTE: chruby-fish and fnm will automatically manage PATH for Ruby and Node versions, so we don't need to manually add them here. Just ensure their initialization scripts are sourced below.
# For Ruby, chruby-fish will handle switching between versions and updating PATH accordingly.
# For Node, fnm will set up the PATH for the active version when initialized.
# This keeps our PATH clean and lets the version managers do their job without conflicts.
# If you have other language runtimes (like Python with pyenv), you can add their initialization here as well, following the same pattern.
# Example for Python with pyenv (if you use it):
# if test -d $HOME/.pyenv and type -q pyenv
#     set -gx PYENV_ROOT $HOME/.pyenv
#     set -gx PATH $PYENV_ROOT/bin $PATH 
#     pyenv init --path | source 
#     pyenv init - | source 
#     pyenv virtualenv-init - | source 
#     #     # Optional: set a global Python version 
#     if type -q pyenv and test -d $HOME/.pyenv/versions/3.15.2
#     pyenv global 3.15.2
#     end
#     # end
#     This example is commented out since you didn't mention Python, but you can easily enable it if you decide to use pyenv in the future. Just make sure to adjust the version number as needed.
#     The key point is that for language runtimes managed by version managers, we rely on their initialization scripts to set up the PATH and environment variables correctly, rather than hardcoding paths in our config.fish. This keeps things flexible and allows the version managers to do their job without conflicts.

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

end

# ============================================
# SSH Agent Health Check
# ============================================
# SECURITY: Use 1Password SSH agent when available, but fall back to
# macOS native agent if the socket is missing (prevents IDE background
# terminal stalling when Touch ID can't be displayed — see Lesson 0i).
set -l op_sock "$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
if test -S $op_sock
    set -gx SSH_AUTH_SOCK $op_sock
else
    # Fallback: use macOS native SSH agent
    set -l mac_sock (command launchctl getenv SSH_AUTH_SOCK 2>/dev/null)
    if test -n "$mac_sock" -a -S "$mac_sock"
        set -gx SSH_AUTH_SOCK $mac_sock
    end
end

# ============================================
# Environment Variables
# ============================================
set -gx NM_ROOT /Users/speedybee/dev/personal-config

# Default Editor (NeoVim)
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

# Make FZF use 'fd' to respect .gitignore and ignore hidden .git folders
if type -q fd
    set -gx FZF_DEFAULT_COMMAND "fd --type f --hidden --exclude .git"
    set -gx FZF_CTRL_T_COMMAND $FZF_DEFAULT_COMMAND
end

# ============================================
# Functions
# ============================================

# --- Git Mirror Clean ---
# Cleans local repo to perfectly match the remote origin/main
function git-mirror-clean --description 'Switch to main, prune remotes, and delete all other local branches'
    # 1. Ensure we are on main
    git checkout main
    or return 1

    # 2. Sync with remote and prune stale tracking refs
    echo "Pruning remote branches..."
    git fetch --prune

    # 3. Delete all local branches except main
    # Using 'string trim' to handle fish whitespace and 'grep -v' to protect main
    set -l branches (git branch | string trim | grep -v '^*' | grep -v '^main$')
    if test -n "$branches"
        echo "Deleting local branches: $branches"
        echo $branches | xargs git branch -D
    else
        echo "No extra local branches to delete."
    end

    # 4. Hard reset main to match origin exactly
    echo "Resetting main to origin/main..."
    git reset --hard origin/main

    # 5. Fix the remote HEAD pointer
    git remote set-head origin -a

    echo "✨ Repository is now a perfect mirror of origin/main"
end

# Config Management helper
function __run_editor --description 'Run $EDITOR handling definition splitting'
    set -l editor (string split ' ' -- $EDITOR)
    command $editor $argv
end

# Vibe Switcher
function vibe
    ~/.local/bin/auto_vibe.sh $argv[1]
    echo "✨ Vibe switched to: $argv[1]"
end

# ============================================
# Aliases
# ============================================

# Navigation
alias ..    'cd ..'
alias ...   'cd ../..'
alias ....  'cd ../../..'
alias ..... 'cd ../../../..'

alias dev       'cd ~/dev'
alias config    'cd ~/dev/personal-config'
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
abbr -a rm 'rm -i'
abbr -a cp 'cp -i'
abbr -a mv 'mv -i'

# Color Support Fallbacks (BSD vs GNU)
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
abbr -a gmc git-mirror-clean  # Added abbreviation for your new function

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
# Visual Styling
# ============================================
# NOTE: Syntax colors are managed by `fish_config theme choose "Dracula Official"`
# (stored as universals — no need to set in config.fish).
# Prompt colors are managed by Tide via `set -U tide_*_color` universals.
# FZF theming is set above in Environment Variables.
# See: configs/.config/fish/RESTORE_CUSTOMIZATIONS.md for setup instructions.

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
            "Evening vibes activated. Let's make some nocturnal magic. 蝙"

        # Select appropriate greeting set based on time
        set -l greetings  
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
