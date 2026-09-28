#!/usr/bin/env bash
# Run one GitNexus remote sync cycle and stop only after completion is published.
set -euo pipefail

PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PATH
GITNEXUS_BIN="${GITNEXUS_BIN:-/opt/homebrew/bin/gitnexus}"
GITNEXUS_HOME="${GITNEXUS_HOME:-$HOME/.gitnexus}"
LOG_DIR="${LOG_DIR:-$HOME/Library/Logs/maintenance}"
WATCH_CONFIG="$GITNEXUS_HOME/watch_config.yml"
WATCH_DIR="$GITNEXUS_HOME/watch"
RUN_POINTER="$WATCH_DIR/maintenance-one-cycle.log-path"
STATE_FILE="$WATCH_DIR/auto-sync-state.json"
MAX_WAIT_SECONDS="${GITNEXUS_AUTO_SYNC_MAX_WAIT_SECONDS:-21600}"
POLL_SECONDS="${GITNEXUS_AUTO_SYNC_POLL_SECONDS:-5}"
MANUAL=0
FORCE_TARGET_EMBEDDINGS=0

for arg in "$@"; do
  case "$arg" in
    --manual) MANUAL=1 ;;
    --force-target-embeddings) FORCE_TARGET_EMBEDDINGS=1 ;;
    *) printf "Usage: %s [--manual] [--force-target-embeddings]\n" "$0" >&2; exit 64 ;;
  esac
done

mkdir -p "$LOG_DIR" "$WATCH_DIR"
RUN_ID="$(date "+%Y%m%d-%H%M%S")-$$"
LOG_FILE="$LOG_DIR/gitnexus-auto-sync-$RUN_ID.log"
START_EPOCH="$(date "+%s")"
FINISHED=0

log() {
  printf "[%s] %s\n" "$(date "+%Y-%m-%dT%H:%M:%S%z")" "$*" | tee -a "$LOG_FILE"
}
on_exit() {
  local rc=$?
  if [[ "$FINISHED" -eq 0 ]]; then
    log "End time: $(date "+%Y-%m-%dT%H:%M:%S%z"); wrapper_exit=$rc"
  fi
}
trap on_exit EXIT
log "Start time: $(date "+%Y-%m-%dT%H:%M:%S%z"); mode=$([[ "$MANUAL" -eq 1 ]] && printf manual || printf scheduled)"

if [[ "$MANUAL" -eq 0 ]]; then
  scheduled_window="$(date "+%H%M")"
  if (( 10#$scheduled_window < 200 || 10#$scheduled_window > 204 )); then
    log "SKIPPED: outside the 2:00-2:04 AM start window; launchd may have fired after wake."
    FINISHED=1
    log "End time: $(date "+%Y-%m-%dT%H:%M:%S%z"); wrapper_exit=0"
    exit 0
  fi
fi

[[ -x "$GITNEXUS_BIN" ]] || { log "ERROR: missing GitNexus executable: $GITNEXUS_BIN"; exit 1; }
[[ -r "$WATCH_CONFIG" ]] || { log "ERROR: unreadable watcher config: $WATCH_CONFIG"; exit 1; }
grep -Eq "^max_concurrency:[[:space:]]*1[[:space:]]*$" "$WATCH_CONFIG" || { log "ERROR: max_concurrency must remain 1."; exit 1; }
grep -Eq "^sync_interval_minutes:[[:space:]]*35791[[:space:]]*$" "$WATCH_CONFIG" || { log "ERROR: sync_interval_minutes must remain 35791 to prevent a follow-up cycle."; exit 1; }
if grep -Eiq "repoprompt|repo-prompt" "$WATCH_CONFIG"; then
  log "ERROR: RepoPrompt appears in config; refusing to run."
  exit 1
fi

CLONE_ROOT="$HOME/dev/.gitnexus-auto-sync/github.com/abhimehro"
python3 - "$CLONE_ROOT" << "PY"
import json
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
for name in ("personal-config", "ctrld-sync", "Seatek_Analysis"):
    path = root / name / ".gitnexusrc"
    try:
        config = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: invalid or missing {path}: {exc}")
    if config.get("embeddings") is not True:
        raise SystemExit(f"ERROR: embeddings must be true in {path}")
    print(f"Embeddings policy verified: {name}=true")
PY

status_output="$("$GITNEXUS_BIN" auto-sync status 2>&1)" || { log "ERROR: cannot read watcher status: $status_output"; exit 1; }
state="$(printf "%s\n" "$status_output" | awk -F= "/^state=/ {split(\$2, fields, \" \"); print fields[1]; exit}")"
if [[ "$state" == "running" ]]; then
  prior_log=""
  if [[ -r "$RUN_POINTER" ]]; then prior_log="$(cat "$RUN_POINTER")"; fi
  if [[ -n "$prior_log" && -f "$prior_log" ]] && grep -Fq "[auto-sync] Watch loop finished:" "$prior_log"; then
    log "Prior cycle completed; requesting clean shutdown. Log: $prior_log"
    "$GITNEXUS_BIN" auto-sync stop >>"$LOG_FILE" 2>&1 || { log "ERROR: clean recovery stop failed; watcher left untouched."; exit 1; }
    rm -f "$RUN_POINTER"
    printf "[%s] Recovery: stopped after completion.\n" "$(date "+%Y-%m-%dT%H:%M:%S%z")" >>"$prior_log"
    FINISHED=1
    log "End time: $(date "+%Y-%m-%dT%H:%M:%S%z"); recovered_previous_run=true"
    exit 0
  fi
  log "ERROR: watcher already running; not starting another cycle or stopping it."
  exit 1
fi
[[ "$state" == "stopped" ]] || { log "ERROR: watcher state is $state, not stopped; refusing to clear state or start."; exit 1; }

if [[ "$FORCE_TARGET_EMBEDDINGS" -eq 1 ]]; then
  backup="$STATE_FILE.pre-embedding-rebuild-$RUN_ID.bak"
  python3 - "$STATE_FILE" "$backup" "$CLONE_ROOT" << "PY"
import json
import os
import pathlib
import shutil
import sys
state_path = pathlib.Path(sys.argv[1])
backup_path = pathlib.Path(sys.argv[2])
root = pathlib.Path(sys.argv[3])
data = json.loads(state_path.read_text())
expected = [root / name for name in ("personal-config", "ctrld-sync", "Seatek_Analysis")]
for repo in expected:
    key = str(repo.resolve()) + "|main"
    if key not in data or not isinstance(data[key], dict):
        raise SystemExit(f"Missing valid auto-sync state entry: {key}")
    if not isinstance(data[key].get("analyzedCommitId"), str):
        raise SystemExit(f"Unexpected analyzedCommitId value for {key}")
shutil.copy2(state_path, backup_path)
for repo in expected:
    key = str(repo.resolve()) + "|main"
    data[key]["analyzedCommitId"] = ""
    data[key]["lastAnalyzeStatus"] = "skipped"
tmp = state_path.with_name(state_path.name + ".tmp.force-embeddings")
tmp.write_text(json.dumps(data, indent=2) + "\n")
os.replace(tmp, state_path)
print("Forced analysis for: personal-config, ctrld-sync, Seatek_Analysis")
print(f"Pre-change auto-sync state backup: {backup_path}")
PY
  log "One-time force enabled for the three embeddings-selected indexes; all other repo state remains unchanged."
fi

pointer_tmp="$RUN_POINTER.tmp.$$"
printf "%s\n" "$LOG_FILE" > "$pointer_tmp"
mv -f "$pointer_tmp" "$RUN_POINTER"
log "Starting one auto-sync cycle with reduced CPU priority (nice 10)."
nice -n 10 "$GITNEXUS_BIN" auto-sync start >>"$LOG_FILE" 2>&1 &
watch_cli_pid=$!

while ! grep -Fq "[auto-sync] Watch loop finished:" "$LOG_FILE"; do
  if ! kill -0 "$watch_cli_pid" 2>/dev/null; then
    wait "$watch_cli_pid" || true
    log "ERROR: GitNexus exited before publishing its completion signal; no forced cleanup attempted."
    exit 1
  fi
  elapsed=$(( $(date "+%s") - START_EPOCH ))
  if (( elapsed >= MAX_WAIT_SECONDS )); then
    FINISHED=1
    log "TIMEOUT: no completion after ${MAX_WAIT_SECONDS}s. Exiting without stopping or killing the active watcher/analyzer; review this run manually."
    log "End time: $(date "+%Y-%m-%dT%H:%M:%S%z"); wrapper_exit=75; watcher_left_running=true"
    exit 75
  fi
  sleep "$POLL_SECONDS"
done

log "Completion signal received; requesting graceful watcher stop."
"$GITNEXUS_BIN" auto-sync stop >>"$LOG_FILE" 2>&1 || { log "ERROR: stop command failed; no signal escalation attempted."; exit 1; }
stopped=0
for _ in $(seq 1 30); do
  status_output="$("$GITNEXUS_BIN" auto-sync status 2>&1 || true)"
  state="$(printf "%s\n" "$status_output" | awk -F= "/^state=/ {split(\$2, fields, \" \"); print fields[1]; exit}")"
  if [[ "$state" == "stopped" ]]; then stopped=1; break; fi
  sleep 1
done
[[ "$stopped" -eq 1 ]] || { log "ERROR: watcher did not report stopped; leaving it untouched."; exit 1; }
wait "$watch_cli_pid" || { log "ERROR: watcher stopped but CLI returned non-zero."; exit 1; }

python3 - "$GITNEXUS_HOME/watch/project_commit_info.txt" << "PY" | tee -a "$LOG_FILE"
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
if not path.is_file():
    print("Repository outcomes unavailable: result file missing.")
    raise SystemExit
remote = None
for line in path.read_text(errors="replace").splitlines():
    if line.startswith("remote: "):
        remote = line.partition(": ")[2].strip()
    elif line.startswith("status: ") and remote:
        name = remote.rsplit("/", 1)[-1].removesuffix(".git")
        status = line.partition(": ")[2].strip()
        label = {"success": "ANALYZED", "skipped": "SKIPPED", "failed": "FAILED", "threshold_skipped": "THRESHOLD_SKIPPED"}.get(status, status.upper())
        print(f"Repository outcome: {name}={label}")
        remote = None
PY

rm -f "$RUN_POINTER"
FINISHED=1
log "End time: $(date "+%Y-%m-%dT%H:%M:%S%z"); watcher_state=stopped"
