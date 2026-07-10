# shellcheck shell=bash
# 1Password CLI shell plugins
# SECURITY: Skip plugin aliases in agent/CI/non-TTY shells so biometric/GUI
# prompts cannot block automation. Interactive human shells keep full UX.
# Override: OP_AGENT_SKIP=0 forces aliases on; OP_AGENT_SKIP=1 forces skip.
#
# Managed copy also lives in personal-config (configs/op/plugins.sh).
# NOTE: `op plugin init` may overwrite this file — re-apply the gate after.

export OP_PLUGIN_ALIASES_SOURCED=1

_op_skip_plugin_aliases=0
case "${OP_AGENT_SKIP-}" in
1 | true | TRUE | yes | YES) _op_skip_plugin_aliases=1 ;;
0 | false | FALSE | no | NO) _op_skip_plugin_aliases=0 ;;
*)
	if [ -n "${CURSOR_AGENT-}" ] || [ -n "${CI-}" ] || [ -n "${GITHUB_ACTIONS-}" ] ||
		[ -n "${CLAUDECODE-}" ] || [ -n "${CODEX_CI-}" ] || [ -n "${AGENT_TOOL-}" ]; then
		_op_skip_plugin_aliases=1
	elif [ ! -t 0 ] && [ ! -t 1 ]; then
		# Non-interactive (no TTY on stdin/stdout): avoid hanging on auth UI
		_op_skip_plugin_aliases=1
	fi
	;;
esac

if [ "$_op_skip_plugin_aliases" -eq 0 ]; then
	alias brew="op plugin run -- brew"
fi
unset _op_skip_plugin_aliases
