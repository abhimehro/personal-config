
# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
if test -f /opt/anaconda3/bin/conda
    eval /opt/anaconda3/bin/conda "shell.fish" "hook" $argv | source
else
    if test -f "/opt/anaconda3/etc/fish/conf.d/conda.fish"
        . "/opt/anaconda3/etc/fish/conf.d/conda.fish"
    else
        set -x PATH "/opt/anaconda3/bin" $PATH
    end
end
# <<< conda initialize <<<


# Added by LM Studio CLI (lms)
set -gx PATH $PATH /Users/abhimehrotra/.cache/lm-studio/bin

set -gx PATH $PATH $HOME/.local/bin

# Network Mode Manager - Control D and Windscribe integration
set -gx NM_ROOT $HOME/Documents/dev/personal-config

# Fish Theme Configuration
# To set ayu-mirage theme, run: fish_config theme choose "ayu Mirage"
# Or install via: fisher install ayu-theme/fish-ayu
# Then set: set -U fish_theme ayu-mirage
#
# Note: Themes are typically managed via fish_config command or fisher plugins.
# Run 'fish_config' to open the theme selector GUI, or install themes via fisher.
