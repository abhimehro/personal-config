# 1Password CLI shell plugins (fish)
# SECURITY: Skip plugin aliases in agent/CI/non-TTY shells so biometric/GUI
# prompts cannot block automation. Interactive human shells keep full UX.
# Override: OP_AGENT_SKIP=0 forces aliases on; OP_AGENT_SKIP=1 forces skip.
#
# Managed copy also lives in personal-config (configs/op/op-plugin-loader.fish).
# NOTE: `op plugin init` may overwrite ~/.config/op/plugins.sh -- re-apply the gate after.

set -gx OP_PLUGIN_ALIASES_SOURCED 1

set _op_skip_plugin_aliases 0
switch "$OP_AGENT_SKIP"
  case 1 true TRUE yes YES
    set _op_skip_plugin_aliases 1
  case 0 false FALSE no NO
    set _op_skip_plugin_aliases 0
  case "*"
    if set -q CURSOR_AGENT; or set -q CI; or set -q GITHUB_ACTIONS; or set -q CLAUDECODE; or set -q CODEX_CI; or set -q AGENT_TOOL
      set _op_skip_plugin_aliases 1
    else if not isatty stdin; and not isatty stdout
      # Non-interactive (no TTY on stdin/stdout): avoid hanging on auth UI
      set _op_skip_plugin_aliases 1
    end
end

if test "$_op_skip_plugin_aliases" -eq 0
  alias agent="op plugin run -- agent"
  alias copilot="op plugin run -- copilot"
  alias gh="op plugin run -- gh"
  alias gemini="op plugin run -- gemini"
  alias huggingface-cli="op plugin run -- huggingface-cli"
  alias vercel="op plugin run -- vercel"
end
set -e _op_skip_plugin_aliases
