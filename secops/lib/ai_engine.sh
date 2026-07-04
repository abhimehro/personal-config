#!/usr/bin/env bash
# shellcheck shell=bash
# ==============================================================================
# SHARED: AI DIAGNOSTIC ENGINE (tiered, timeout-safe)
# ==============================================================================
# Part of SecOps Autopilot. Sourced by phase scripts.
#
# Provides:
#   run_timeout <seconds> <cmd...>   - hard wall-clock cap (macOS has no `timeout`)
#   ai_diagnose <prompt>             - reads a log on stdin, asks an AI CLI to
#                                      analyze it, NEVER hangs, NEVER fails the
#                                      caller. Falls back through engines and
#                                      finally to the raw log.
#
# Engine order (most→least reliable headless, configurable via SECOPS_AI_ENGINE):
#   1. vibe         (Mistral Vibe: `vibe -p "<prompt>"`)      -- PRIMARY. Verified
#                   working headlessly on this machine; returns clean text.
#   2. raw          (cat the log)                             -- always works
#
# OPT-IN engines (NOT in the default chain — each has a known headless failure
# on this machine; enable explicitly via SECOPS_AI_ENGINE if/when fixed):
#   - copilot       (`copilot -p`)        Broken install: the pinned package
#                   index (~/Library/Caches/copilot/pkg/.../index.js) is missing
#                   → ERR_MODULE_NOT_FOUND on every invocation. Reinstall the
#                   GitHub Copilot CLI to restore. User also deprioritizes it.
#   - cursor-agent  (`cursor-agent -p --output-format text -f`) Logged in, but
#                   print/headless mode returns empty and spawns child node
#                   procs that outlive a kill of the immediate child (escapes
#                   the timeout). Needs investigation before re-enabling.
#   - gemini        (`gemini -m <model> -p`) OAuth-personal path blocks
#                   indefinitely in a non-TTY/launchd context and the configured
#                   model has 404'd; previously wedged Phase 3 for 40+ min.
#
# NOTE: cursor-agent uses `-f`/`--force` (a.k.a. `--yolo`), NOT `--trust`.
# vibe takes the prompt as the argument to `-p` directly: `vibe -p "<prompt>"`.
# ==============================================================================

# Hard timeout using perl alarm (portable on stock macOS; no coreutils needed).
# Runs the child in its OWN process group (setpgid) and kills the WHOLE group on
# timeout, so node/python helpers spawned by the AI CLI can't survive and wedge
# the daemon. This was the root cause of multi-minute hangs (cursor-agent,
# gemini) escaping the old single-PID kill.
run_timeout() {
	local secs="$1"
	shift
	perl -e '
    use POSIX qw(setpgid);
    my $t = shift @ARGV;
    my $pid = fork();
    if (!defined $pid) { exit 127; }
    if ($pid == 0) { setpgid(0, 0); exec @ARGV; exit 127; }
    setpgid($pid, $pid);
    local $SIG{ALRM} = sub { kill(-9, $pid); waitpid $pid, 0; exit 124; };
    alarm $t;
    waitpid $pid, 0;
    alarm 0;          # cancel pending alarm to close the race between waitpid returning and exit($rc) below
    my $rc = $? >> 8;
    kill(-9, $pid);   # reap any lingering group members
    exit($rc);
  ' "$secs" "$@"
}

# Per-call wall-clock budget for any single AI engine attempt.
: "${SECOPS_AI_TIMEOUT:=60}"
# Default chain = only engines verified to work headlessly here. Override to
# re-enable others once fixed, e.g. SECOPS_AI_ENGINE="vibe cursor-agent raw"
: "${SECOPS_AI_ENGINE:=vibe raw}"

_ai_try_copilot() {
	local prompt="$1" log="$2"
	command -v copilot &>/dev/null || return 2
	local out
	out="$(run_timeout "$SECOPS_AI_TIMEOUT" copilot -p \
		"${prompt}

--- LOG START ---
$(cat "$log")
--- LOG END ---" 2>/dev/null)"
	# Guard: a broken install prints ERR_MODULE_NOT_FOUND / "Failed to load
	# package index" to stdout. Treat that as "not available" so the chain falls
	# through instead of accepting an error string as a diagnosis.
	case "$out" in
	*ERR_MODULE_NOT_FOUND* | *"Failed to load package index"*) return 2 ;;
	esac
	printf '%s\n' "$out"
}

_ai_try_cursor-agent() {
	local prompt="$1" log="$2"
	command -v cursor-agent &>/dev/null || return 2
	# NOTE: cursor-agent has no --trust flag; -f/--force is the non-interactive
	# "allow all" switch. Prompt is the trailing positional.
	run_timeout "$SECOPS_AI_TIMEOUT" cursor-agent -p --output-format text -f \
		"${prompt}

--- LOG START ---
$(cat "$log")
--- LOG END ---" 2>/dev/null
}

_ai_try_vibe() {
	local prompt="$1" log="$2"
	command -v vibe &>/dev/null || return 2
	# vibe takes the prompt as the argument to -p DIRECTLY. Passing other flags
	# between -p and the prompt makes vibe see no prompt ("No prompt provided for
	# programmatic mode"). --agent auto-approve = non-interactive. Strip the
	# pyshim warning line from output.
	run_timeout "$SECOPS_AI_TIMEOUT" vibe -p "${prompt}

--- LOG START ---
$(cat "$log")
--- LOG END ---" --agent auto-approve --output text 2>/dev/null | grep -v '^\[ara-pyshim\]'
}

_ai_try_gemini() {
	local prompt="$1" log="$2"
	command -v gemini &>/dev/null || return 2
	local model="${SECOPS_GEMINI_MODEL:-gemini-2.5-flash}"
	run_timeout "$SECOPS_AI_TIMEOUT" gemini -m "$model" -p \
		"${prompt}

--- LOG START ---
$(cat "$log")
--- LOG END ---" 2>/dev/null
}

_ai_try_raw() {
	local prompt="$1" log="$2"
	echo "[ai_diagnose] No AI engine available; raw log follows:"
	cat "$log"
}

# ai_diagnose <prompt>   (reads log from stdin)
ai_diagnose() {
	local prompt="$1"
	local tmp
	tmp="$(mktemp "${TMPDIR:-/tmp}/secops_ai.XXXXXX")"
	cat - >"$tmp"

	local engine out rc
	for engine in $SECOPS_AI_ENGINE; do
		# Self-enforcing fail-safe: capture rc via `|| rc=$?` so a non-zero
		# engine result (rc=2 missing, rc=124 timeout, etc.) never trips
		# `set -e` in a caller that forgot to guard the call site. The `||`
		# branch preserves the real exit code for the fallback dispatch below.
		rc=0
		out="$("_ai_try_${engine}" "$prompt" "$tmp")" || rc=$?
		# rc 2 = engine not installed; 124 = timed out; skip to next.
		if [ "$rc" -eq 2 ] || [ "$rc" -eq 124 ]; then
			[ "$rc" -eq 124 ] && echo "[ai_diagnose] engine '$engine' timed out after ${SECOPS_AI_TIMEOUT}s, falling back." >&2
			continue
		fi
		# Accept the first engine that produced non-empty output.
		if [ -n "${out//[[:space:]]/}" ]; then
			echo "[ai_diagnose] engine: $engine"
			echo "$out"
			rm -f "$tmp"
			return 0
		fi
	done

	rm -f "$tmp"
	return 0
}
