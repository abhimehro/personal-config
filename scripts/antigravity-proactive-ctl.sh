#!/usr/bin/env bash
#
# Control and Ordered-Rollback Script for Antigravity Proactive Workflows.
# Manages global skill symlinks, PreToolUse safety hook link, chmod 700 report
# and transcript permissions, staged sidecars (without ever self-enabling
# user_config.json), disposable UTC cron canaries, verified post-merge Sentinel
# leases, and MISSED slot auditing.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SKILLS=(
	"proactive-sentinel"
	"proactive-bolt"
	"proactive-palette"
	"proactive-code-health"
	"proactive-repo-sweep"
)

PILOT_SIDECAR_ID="proactive-pilot-ctrld-sync"
TRIAGE_SIDECAR_ID="proactive-pilot-triage"
CANARY_SIDECAR_ID="proactive-cron-canary"

usage() {
	cat <<'EOF'
Usage:
  antigravity-proactive-ctl.sh install [--pilot]
  antigravity-proactive-ctl.sh status
  antigravity-proactive-ctl.sh canary-stage [--offset-minutes <n>]
  antigravity-proactive-ctl.sh canary-clean
  antigravity-proactive-ctl.sh sentinel-post-merge --repo <name> --pr <number>
  antigravity-proactive-ctl.sh audit-missed --date <YYYY-MM-DD> --repo <name>
  antigravity-proactive-ctl.sh disable
EOF
}

link_item() {
	local link_path="$1"
	local target_path="$2"

	if [[ ! -e ${target_path} ]]; then
		echo "[ERROR] Missing target in repository: ${target_path}" >&2
		exit 1
	fi

	if [[ -L ${link_path} ]] && [[ "$(readlink "${link_path}")" == "${target_path}" ]]; then
		return 0
	fi

	if [[ -e ${link_path} ]] && [[ ! -L ${link_path} ]]; then
		local backup_ts
		backup_ts="$(date -u +%Y%m%d_%H%M%S)"
		mv "${link_path}" "${link_path}.backup.${backup_ts}"
	fi

	if [[ -L ${link_path} ]]; then
		rm -f "${link_path}"
	fi

	mkdir -p "$(dirname "${link_path}")"
	ln -s "${target_path}" "${link_path}"
}

cmd_install() {
	local stage_pilot=0
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--pilot)
			stage_pilot=1
			shift
			;;
		*)
			echo "[ERROR] Unknown flag for install: $1" >&2
			exit 1
			;;
		esac
	done

	local config_dir="${HOME}/.gemini/config"
	local agy_dir="${HOME}/.gemini/antigravity"
	local cli_dir="${HOME}/.gemini/antigravity-cli"
	local skills_dir="${config_dir}/skills"
	local reports_dir="${agy_dir}/proactive-reports"
	local worktrees_dir="${agy_dir}/worktrees"

	mkdir -p "${skills_dir}" "${reports_dir}" "${worktrees_dir}"
	chmod 700 "${reports_dir}" "${worktrees_dir}"
	if [[ -d "${agy_dir}/brain" ]]; then
		chmod 700 "${agy_dir}/brain" 2>/dev/null || true
	fi
	if [[ -d ${cli_dir} ]]; then
		chmod 700 "${cli_dir}" 2>/dev/null || true
	fi

	local skill=""
	for skill in "${SKILLS[@]}"; do
		link_item \
			"${skills_dir}/${skill}" \
			"${REPO_ROOT}/configs/antigravity/skills/${skill}"
	done

	link_item \
		"${config_dir}/hooks.json" \
		"${REPO_ROOT}/configs/antigravity/hooks.json"

	if [[ ${stage_pilot} -eq 1 ]]; then
		local sid=""
		for sid in "${PILOT_SIDECAR_ID}" "${TRIAGE_SIDECAR_ID}"; do
			local sidecar_src="${REPO_ROOT}/configs/antigravity/sidecars/${sid}.sidecar.json"
			if [[ -f ${sidecar_src} ]]; then
				local sidecar_dir="${config_dir}/sidecars/${sid}"
				mkdir -p "${sidecar_dir}"
				python3 - "${sidecar_src}" "${sidecar_dir}/sidecar.json" "${HOME}" <<'PY'
import pathlib
import sys

src = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
dst = pathlib.Path(sys.argv[2])
dst.write_text(src.replace("__HOME__", sys.argv[3]), encoding="utf-8")
dst.chmod(0o600)
PY
			fi
		done
		# Never create or modify user_config.json; human enables in sidecar://dashboard.
	fi

	echo "Installed Antigravity proactive configuration (pilot_sidecar=${stage_pilot})"
}

cmd_status() {
	local config_dir="${HOME}/.gemini/config"
	local agy_dir="${HOME}/.gemini/antigravity"
	local linked=0
	local total="${#SKILLS[@]}"
	local skill=""

	for skill in "${SKILLS[@]}"; do
		if [[ -L "${config_dir}/skills/${skill}" ]]; then
			linked=$((linked + 1))
		fi
	done

	local hooks_linked="no"
	if [[ -L "${config_dir}/hooks.json" ]]; then
		hooks_linked="yes"
	fi

	local sidecar_file="${config_dir}/sidecars/${PILOT_SIDECAR_ID}/sidecar.json"
	local user_cfg="${config_dir}/sidecars/${PILOT_SIDECAR_ID}/user_config.json"
	local sidecar_state="absent"
	if [[ -f ${sidecar_file} ]]; then
		sidecar_state="present"
	fi

	local enabled_state="unset"
	if [[ -f ${user_cfg} ]]; then
		enabled_state="$(python3 -c 'import json,sys; print(str(json.load(open(sys.argv[1])).get("enabled","unset")).lower())' "${user_cfg}" 2>/dev/null || echo "unknown")"
	fi

	# The dashboard toggle does not necessarily write user_config.json. The live
	# scheduler log under sidecar_data/ is the authoritative runtime signal.
	local runtime_log="${agy_dir}/sidecar_data/${PILOT_SIDECAR_ID}/logs/sidecar.log"
	local runtime_state="stopped"
	local next_run="n/a"
	if [[ -f ${runtime_log} ]]; then
		local last_state_line=""
		last_state_line="$(grep -E 'Scheduler started|Shutting down' "${runtime_log}" | tail -n 1 || true)"
		if [[ ${last_state_line} == *"Scheduler started"* ]]; then
			runtime_state="running"
			next_run="$(grep -E 'Next execution scheduled' "${runtime_log}" | tail -n 1 | sed -n 's/.*(at \([^)]*\)).*/\1/p' || true)"
			[[ -n ${next_run} ]] || next_run="unknown"
		fi
	fi

	local canary_state="absent"
	if [[ -f "${config_dir}/sidecars/${CANARY_SIDECAR_ID}/sidecar.json" ]]; then
		canary_state="present"
	fi

	echo "skills_linked=${linked}/${total}"
	echo "hooks_linked=${hooks_linked}"
	echo "pilot_sidecar=${sidecar_state}"
	echo "pilot_user_enabled=${enabled_state}"
	echo "pilot_runtime=${runtime_state}"
	echo "pilot_next_run=${next_run}"
	echo "canary_sidecar=${canary_state}"
	echo "reports_dir=${agy_dir}/proactive-reports"
}

cmd_canary_stage() {
	local offset_min=4
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--offset-minutes)
			offset_min="$2"
			shift 2
			;;
		*)
			echo "[ERROR] Unknown flag for canary-stage: $1" >&2
			exit 1
			;;
		esac
	done

	local config_dir="${HOME}/.gemini/config"
	local reports_dir="${HOME}/.gemini/antigravity/proactive-reports"
	local canary_dir="${config_dir}/sidecars/${CANARY_SIDECAR_ID}"
	mkdir -p "${canary_dir}" "${reports_dir}"
	chmod 700 "${reports_dir}"

	python3 - "${canary_dir}/sidecar.json" "${reports_dir}" "${offset_min}" "${HOME}" <<'PY'
import datetime as dt
import json
import pathlib
import sys

out_path = pathlib.Path(sys.argv[1])
reports_dir = sys.argv[2]
offset = int(sys.argv[3])
home_dir = sys.argv[4]

fire_dt = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=offset)
cron_expr = f"CRON_TZ=UTC {fire_dt.minute} {fire_dt.hour} {fire_dt.day} {fire_dt.month} *"
receipt_path = f"{reports_dir}/canary-utc-receipt.md"

doc = {
    "builtin": "schedule",
    "args": [
        cron_expr,
        "agentapi",
        "new-conversation",
        "--",
        "[PROACTIVE-SWEEP] Disposable UTC cron canary check. "
        f"Run `{home_dir}/bin/agent-zsh -c 'umask 077 && date -u +\"CANARY_FIRED_UTC=%Y-%m-%dT%H:%M:%SZ\" > {receipt_path}'` "
        "and reply ONLY with `CANARY_UTC_OK`.",
    ],
    "restart_policy": "always",
    "display_name": "Proactive Cron Canary (Disposable)",
    "description": f"One-time disposable UTC cron test scheduled for {fire_dt.strftime('%Y-%m-%d %H:%M UTC')}. Remove afterward via antigravity-proactive-ctl.sh canary-clean.",
    "agent_permissions": {
        "allows_user_interactions": False,
        "access_grants": [
            f"write_file({reports_dir})",
            f"command({home_dir}/bin/agent-zsh -c)",
        ],
    },
}
out_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
out_path.chmod(0o600)
print(f"Staged disposable canary for {fire_dt.strftime('%Y-%m-%d %H:%M UTC')} ({cron_expr})")
PY
}

cmd_canary_clean() {
	local canary_dir="${HOME}/.gemini/config/sidecars/${CANARY_SIDECAR_ID}"
	rm -f "${canary_dir}/sidecar.json" "${canary_dir}/user_config.json"
	rmdir "${canary_dir}" 2>/dev/null || true
	echo "Removed disposable cron canary sidecar"
}

cmd_sentinel_post_merge() {
	local repo_name=""
	local pr_num=""
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--repo)
			repo_name="${2##*/}"
			shift 2
			;;
		--pr)
			pr_num="$2"
			shift 2
			;;
		*)
			echo "[ERROR] Unknown flag for sentinel-post-merge: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ -z ${repo_name} ]] || [[ -z ${pr_num} ]]; then
		echo "[ERROR] sentinel-post-merge requires --repo <name> and --pr <number>" >&2
		exit 1
	fi

	local pr_json
	pr_json="$(gh pr view "${pr_num}" --repo "abhimehro/${repo_name}" --json state,mergedAt)"

	local reports_dir="${HOME}/.gemini/antigravity/proactive-reports"
	mkdir -p "${reports_dir}"
	chmod 700 "${reports_dir}"

	python3 - "${pr_json}" "${repo_name}" "${pr_num}" "${reports_dir}/.sentinel-post-merge-lease.json" <<'PY'
import json
import os
import pathlib
import sys
import time

info = json.loads(sys.argv[1])
repo_name = sys.argv[2]
pr_num = int(sys.argv[3])
lease_path = pathlib.Path(sys.argv[4])

if info.get("state") != "MERGED" or not info.get("mergedAt"):
    sys.stderr.write(f"[ERROR] PR #{pr_num} in abhimehro/{repo_name} is not MERGED; refusing to unlock .jules/sentinel.md\n")
    sys.exit(1)

lease = {
    "repo_name": repo_name,
    "merged_pr": pr_num,
    "merged_at": info["mergedAt"],
    "expires_at": time.time() + 300,
}
lease_path.write_text(json.dumps(lease, indent=2) + "\n", encoding="utf-8")
os.chmod(lease_path, 0o600)
print(f"Unlocked post-merge .jules/sentinel.md write for {repo_name} (PR #{pr_num}, 5-minute lease)")
PY
}

cmd_audit_missed() {
	local date_str=""
	local repo_name=""
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--date)
			date_str="$2"
			shift 2
			;;
		--repo)
			repo_name="${2##*/}"
			shift 2
			;;
		*)
			echo "[ERROR] Unknown flag for audit-missed: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ -z ${date_str} ]] || [[ -z ${repo_name} ]]; then
		echo "[ERROR] audit-missed requires --date <YYYY-MM-DD> and --repo <name>" >&2
		exit 1
	fi

	local reports_dir="${HOME}/.gemini/antigravity/proactive-reports"
	mkdir -p "${reports_dir}"
	chmod 700 "${reports_dir}"

	local report_file="${reports_dir}/${date_str}-${repo_name}.md"
	if [[ -f ${report_file} ]]; then
		echo "PRESENT: ${report_file}"
		return 0
	fi

	(
		umask 077
		cat >"${report_file}" <<EOF
# Proactive Sweep Digest (${date_str} - ${repo_name})

- Status: MISSED
- Repository: abhimehro/${repo_name}
- Scheduled Slot: ${date_str} 13:15 UTC
- Reason: No digest recorded for this scheduled slot (host asleep, Antigravity.app closed, or sidecar disabled). Excluded from mergeable-rate denominator.
EOF
		chmod 600 "${report_file}"
	)
	echo "MISSED_RECORDED: ${report_file}"
}

cmd_disable() {
	local config_dir="${HOME}/.gemini/config"

	# Step 1/3: Stop/remove sidecars FIRST so no scheduled sweep can fire unguarded.
	local sid=""
	for sid in "${PILOT_SIDECAR_ID}" "${TRIAGE_SIDECAR_ID}" "${CANARY_SIDECAR_ID}"; do
		local sidecar_dir="${config_dir}/sidecars/${sid}"
		rm -f "${sidecar_dir}/sidecar.json" "${sidecar_dir}/user_config.json"
		rmdir "${sidecar_dir}" 2>/dev/null || true
	done
	echo "Step 1/3: removed sidecar definitions before unlinking safety hooks"

	# Step 2/3: Remove global proactive skill symlinks.
	local skill=""
	for skill in "${SKILLS[@]}"; do
		if [[ -L "${config_dir}/skills/${skill}" ]]; then
			rm -f "${config_dir}/skills/${skill}"
		fi
	done
	echo "Step 2/3: unlinked 5 proactive skill symlinks"

	# Step 3/3: Unlink global hooks.json LAST.
	if [[ -L "${config_dir}/hooks.json" ]]; then
		rm -f "${config_dir}/hooks.json"
		local latest_backup
		latest_backup="$(find "${config_dir}" -maxdepth 1 -name "hooks.json.backup.[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]" -type f 2>/dev/null | sort -r | head -n 1 || true)"
		if [[ -n ${latest_backup} ]] && [[ -f ${latest_backup} ]]; then
			echo "Step 3/3: restored previous hooks.json from ${latest_backup}"
			mv "${latest_backup}" "${config_dir}/hooks.json"
		else
			echo "Step 3/3: unlinked global hooks.json (local reports and worktrees preserved)"
		fi
	else
		echo "Step 3/3: hooks.json already unlinked"
	fi

	cat <<'EOF'
Manual remote restoration steps (if rolling back completely to Google Jules):
  1. Re-enable legacy GitHub Actions workflows (if desired):
     gh variable set ENABLE_LEGACY_JULES --body true --repo abhimehro/personal-config
  2. Re-enable Google Jules remote proactive toggles in the Jules web UI for:
     - abhimehro/ctrld-sync
     - abhimehro/email-security-pipeline
     - abhimehro/Hydrograph_Versus_Seatek_Sensors_Project
     - abhimehro/Seatek_Analysis
     - abhimehro/personal-config
  3. If 2A ruleset/token changes were applied, revert bypass_actors or revoke the automation token as needed.
EOF
}

main() {
	if [[ $# -lt 1 ]]; then
		usage >&2
		exit 1
	fi
	local subcmd="$1"
	shift
	case "${subcmd}" in
	install)
		cmd_install "$@"
		;;
	status)
		cmd_status "$@"
		;;
	canary-stage)
		cmd_canary_stage "$@"
		;;
	canary-clean)
		cmd_canary_clean "$@"
		;;
	sentinel-post-merge)
		cmd_sentinel_post_merge "$@"
		;;
	audit-missed)
		cmd_audit_missed "$@"
		;;
	disable)
		cmd_disable "$@"
		;;
	-h | --help | help)
		usage
		;;
	*)
		echo "[ERROR] Unknown subcommand: ${subcmd}" >&2
		usage >&2
		exit 1
		;;
	esac
}

main "$@"
