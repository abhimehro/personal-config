# Agent zsh environment (non-interactive safe)
# Loaded for ALL zsh invocations when ZDOTDIR points here.
# Keep this file free of prompts, compinit, and interactive widgets.

export LANG="${LANG:-en_US.UTF-8}"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"
export EDITOR="${EDITOR:-nvim}"
export VISUAL="${VISUAL:-nvim}"
export GIT_EDITOR="${GIT_EDITOR:-nvim}"

# Deterministic tooling for agents / CI-like runs
export HOMEBREW_NO_AUTO_UPDATE=1
export HOMEBREW_NO_ANALYTICS=1
export HOMEBREW_NO_ENV_HINTS=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export PAGER="${PAGER:-cat}"
export GIT_PAGER="${GIT_PAGER:-cat}"
export LESS="${LESS:--FRX}"

# Workspace roots
export AGENT_WORKSPACE="${AGENT_WORKSPACE:-$HOME/dev/abhimehro}"
export PERSONAL_CONFIG="${PERSONAL_CONFIG:-$HOME/dev/personal-config}"

# Prefer Homebrew + user bins without clobbering absolute agent paths later
typeset -U path PATH
path=(
  /opt/homebrew/bin
  /opt/homebrew/sbin
  /usr/local/bin
  $HOME/bin
  $HOME/.local/bin
  /usr/bin
  /bin
  /usr/sbin
  /sbin
  $path
)
export PATH

# Quiet, predictable option baseline (safe in non-interactive)
setopt NO_BEEP 2>/dev/null || true
setopt INTERACTIVE_COMMENTS 2>/dev/null || true
setopt PATH_DIRS 2>/dev/null || true
unsetopt GLOBAL_RCS 2>/dev/null || true
unsetopt MONITOR 2>/dev/null || true
unsetopt HUP 2>/dev/null || true

# Auto-cd into workspace for common agent launch dirs (/, $HOME)
# Skip if user already navigated elsewhere.
case "$PWD" in
  /|"$HOME"|"$HOME/")
    if [[ -d "$AGENT_WORKSPACE" ]]; then
      cd "$AGENT_WORKSPACE" 2>/dev/null || true
    fi
    ;;
esac
