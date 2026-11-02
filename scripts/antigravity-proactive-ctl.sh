#!/usr/bin/env bash
#
# Control and Ordered-Rollback Script for Antigravity Proactive Workflows.
# Manages global skill symlinks, PreToolUse safety hook link, chmod 700 report
# and transcript permissions, staged sidecars (without ever self-enabling
# user_config.json), disposable UTC cron canaries, verified post-merge Sentinel
# leases, MISSED slot auditing, and base-relative classification of verify
# failures so pre-existing breakage is never charged to the candidate.

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

# base-check's EXIT trap outlives the function that sets it, so its cleanup state
# has to be global: a `local` would be unbound by then and, under `set -u`, the
# trap itself would fail and mask the real exit status.
BASE_CHECK_WT=""
BASE_CHECK_DIR=""
BASE_CHECK_REPO=""

base_check_cleanup() {
	if [[ -n ${BASE_CHECK_WT} ]] && [[ -d ${BASE_CHECK_WT} ]]; then
		git -C "${BASE_CHECK_REPO}" worktree remove --force "${BASE_CHECK_WT}" >/dev/null 2>&1 || true
		git -C "${BASE_CHECK_REPO}" worktree prune >/dev/null 2>&1 || true
	fi
	if [[ -n ${BASE_CHECK_DIR} ]] && [[ -d ${BASE_CHECK_DIR} ]]; then
		rm -rf "${BASE_CHECK_DIR}"
	fi
}

# Trims a stage split out of an '&&'-joined test command. Uses a character-at-a-time
# loop instead of the ${var#"${var%%[![:space:]]*}"} idiom, which nests quotes badly
# on the bash 3.2 that ships with macOS.
trim_test_segment() {
	local out="$1"
	while [[ ${out} == [[:space:]]* ]]; do out="${out#?}"; done
	while [[ ${out} == *[[:space:]] ]]; do out="${out%?}"; done
	printf '%s' "${out}"
}

usage() {
	cat <<'EOF'
Usage:
  antigravity-proactive-ctl.sh install [--pilot]
  antigravity-proactive-ctl.sh status
  antigravity-proactive-ctl.sh canary-stage [--offset-minutes <n>]
  antigravity-proactive-ctl.sh canary-clean
  antigravity-proactive-ctl.sh sentinel-post-merge --repo <name> --pr <number>
  antigravity-proactive-ctl.sh audit-missed --date <YYYY-MM-DD> --repo <name>
  antigravity-proactive-ctl.sh base-check --repo <name> --worktree <dir> [--digest <path>] [--test-cmd <cmd>]
  antigravity-proactive-ctl.sh disable

base-check exit codes:
  0 NO_FAILURE / FLAKE_ON_RETRY / PRE_EXISTING_ON_BASE (candidate promotable),
  1 usage, 2 CAUSED_BY_CHANGE (real regression, discard the candidate),
  6 could not create a pristine base worktree
EOF
}

validate_repo_name() {
	local name="$1"
	local subcmd="$2"
	# repo_name is interpolated into report and lease paths, so reject separators,
	# ".", ".." and anything else outside a conservative GitHub-name allowlist.
	if [[ ! ${name} =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
		echo "[ERROR] ${subcmd}: invalid --repo name: ${name}" >&2
		exit 1
	fi
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
	validate_repo_name "${repo_name}" "sentinel-post-merge"
	if [[ ! ${pr_num} =~ ^[0-9]+$ ]]; then
		echo "[ERROR] sentinel-post-merge requires a numeric --pr value" >&2
		exit 1
	fi

	local pr_json
	pr_json="$(gh pr view "${pr_num}" --repo "abhimehro/${repo_name}" --json state,mergedAt)"

	local reports_dir="${HOME}/.gemini/antigravity/proactive-reports"
	mkdir -p "${reports_dir}"
	chmod 700 "${reports_dir}"

	python3 - "${pr_json}" "${repo_name}" "${pr_num}" "${reports_dir}/.sentinel-post-merge-lease.json" <<'PY'
import datetime
import json
import os
import pathlib
import sys
import time

# A lease unlocks .jules/sentinel.md writes, so it must follow a merge that just
# happened, not any historical merged PR. The small negative bound only absorbs
# clock skew between GitHub and this host.
MAX_MERGE_AGE_S = 15 * 60
MAX_CLOCK_SKEW_S = 60

info = json.loads(sys.argv[1])
repo_name = sys.argv[2]
pr_num = int(sys.argv[3])
lease_path = pathlib.Path(sys.argv[4])

if info.get("state") != "MERGED" or not info.get("mergedAt"):
    sys.stderr.write(f"[ERROR] PR #{pr_num} in abhimehro/{repo_name} is not MERGED; refusing to unlock .jules/sentinel.md\n")
    sys.exit(1)

merged_at = datetime.datetime.fromisoformat(info["mergedAt"].replace("Z", "+00:00"))
age_s = (datetime.datetime.now(datetime.timezone.utc) - merged_at).total_seconds()
if age_s > MAX_MERGE_AGE_S or age_s < -MAX_CLOCK_SKEW_S:
    sys.stderr.write(
        f"[ERROR] PR #{pr_num} in abhimehro/{repo_name} merged at {info['mergedAt']} "
        f"({int(age_s)}s ago), outside the {MAX_MERGE_AGE_S // 60}-minute post-merge window; "
        "refusing to unlock .jules/sentinel.md\n"
    )
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
	if [[ ! ${date_str} =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
		echo "[ERROR] audit-missed --date must be YYYY-MM-DD, got: ${date_str}" >&2
		exit 1
	fi
	validate_repo_name "${repo_name}" "audit-missed"

	# The pilot sidecar fires at 08:15 America/Chicago, which is 13:15 UTC only under
	# daylight time and 14:15 UTC under standard time. Resolve the real UTC instant
	# for this date (this also rejects impossible dates such as 2026-02-30).
	local slot_utc
	if ! slot_utc="$(
		python3 - "${date_str}" <<'PY'
import datetime
import sys
import zoneinfo

day = datetime.date.fromisoformat(sys.argv[1])
local = datetime.datetime.combine(
    day, datetime.time(8, 15), tzinfo=zoneinfo.ZoneInfo("America/Chicago")
)
print(local.astimezone(datetime.timezone.utc).strftime("%H:%M"))
PY
	)"; then
		echo "[ERROR] audit-missed --date is not a valid calendar date: ${date_str}" >&2
		exit 1
	fi
	local slot_desc="${date_str} 08:15 America/Chicago (${slot_utc} UTC)"

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
- Scheduled Slot: ${slot_desc}
- Reason: No digest recorded for this scheduled slot (host asleep, Antigravity.app closed, or sidecar disabled). Excluded from mergeable-rate denominator.
EOF
		chmod 600 "${report_file}"
	)
	echo "MISSED_RECORDED: ${report_file}"
}

# G-4: a verify failure is not automatically the candidate's fault. Jules stranded
# four good PRs on breakage the change did not cause — deleting a
# cyclomatic-complexity-1 helper *lowered* CodeScene health and failed the gate,
# two unrelated shards flaked, and a morning-brief PR was blocked by a
# refactoring-agent test failure. Re-run the failing stage on a pristine base
# worktree so the verdict is relative to base rather than absolute. This lives in
# the 08:35 triage slot, not inside the sweep, because a base re-run can double
# test time and the sweep is boxed at 15 minutes.
cmd_base_check() {
	local repo_name=""
	local wt_path=""
	local digest=""
	local test_cmd=""

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--repo)
			repo_name="${2##*/}"
			shift 2
			;;
		--worktree)
			wt_path="$2"
			shift 2
			;;
		--digest)
			digest="$2"
			shift 2
			;;
		--test-cmd)
			test_cmd="$2"
			shift 2
			;;
		*)
			echo "[ERROR] Unknown flag for base-check: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ -z ${repo_name} ]] || [[ -z ${wt_path} ]]; then
		echo "[ERROR] base-check requires --repo <name> and --worktree <dir>" >&2
		exit 1
	fi
	validate_repo_name "${repo_name}" "base-check"
	if [[ ! -d ${wt_path} ]]; then
		echo "[ERROR] base-check --worktree is not a directory: ${wt_path}" >&2
		exit 1
	fi
	if [[ -n ${digest} ]] && [[ ! -f ${digest} ]]; then
		echo "[ERROR] base-check --digest does not exist: ${digest}" >&2
		exit 1
	fi

	local wt_git_dir=""
	wt_git_dir="$(git -C "${wt_path}" rev-parse --git-dir 2>/dev/null || true)"
	if [[ -z ${wt_git_dir} ]]; then
		echo "[ERROR] base-check --worktree is not inside a git worktree: ${wt_path}" >&2
		exit 1
	fi
	local meta_file="${wt_git_dir}/proactive-meta.json"
	if [[ ! -f ${meta_file} ]]; then
		echo "[ERROR] base-check needs a prepared proactive worktree; missing proactive-meta.json in ${wt_git_dir}" >&2
		exit 1
	fi

	local meta_repo="" base_sha=""
	meta_repo="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("repo_name",""))' "${meta_file}" 2>/dev/null || true)"
	base_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("base_sha",""))' "${meta_file}" 2>/dev/null || true)"
	if [[ ${meta_repo} != "${repo_name}" ]]; then
		echo "[ERROR] base-check --repo ${repo_name} does not match the worktree's repo_name '${meta_repo}'" >&2
		exit 1
	fi
	if [[ -z ${base_sha} ]]; then
		echo "[ERROR] base-check cannot classify without a recorded base_sha in ${meta_file}" >&2
		exit 1
	fi

	# Share one repo->test-command mapping with verify instead of duplicating it.
	if [[ -z ${test_cmd} ]]; then
		test_cmd="$("${SCRIPT_DIR}/proactive-worktree.sh" print-test-cmd --repo-name "${repo_name}")"
	fi
	if [[ -z ${test_cmd} ]]; then
		echo "[ERROR] base-check resolved an empty test command for ${repo_name}" >&2
		exit 1
	fi

	# Split the compound command on '&&' so one failing stage can be re-run on base
	# instead of paying for the whole suite twice. A literal '&&' inside a quoted
	# argument would split wrongly; none of the current repo mappings contain one.
	local segments=()
	local rest="${test_cmd}"
	while [[ ${rest} == *"&&"* ]]; do
		segments+=("$(trim_test_segment "${rest%%&&*}")")
		rest="${rest#*&&}"
	done
	segments+=("$(trim_test_segment "${rest}")")

	BASE_CHECK_REPO="${wt_path}"
	BASE_CHECK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/proactive-basecheck.XXXXXX")"
	trap base_check_cleanup EXIT

	# No origin ref is consulted: the comparison is candidate vs a local base_sha,
	# so this classification stays valid offline and needs no fetch precondition.
	BASE_CHECK_WT="${BASE_CHECK_DIR}/base"
	if ! git -C "${wt_path}" worktree add --detach "${BASE_CHECK_WT}" "${base_sha}" >/dev/null 2>&1; then
		echo "[ERROR] could not create a pristine base worktree at ${base_sha}; the object may have been gc'd" >&2
		exit 6
	fi

	# Credentials are stripped for the same reason verify strips them: a gate must
	# not pass because the ambient environment can reach a remote.
	run_segment_in() {
		local dir="$1"
		local seg="$2"
		local log="$3"
		(
			cd "${dir}" || exit 1
			env -u SSH_AUTH_SOCK -u GH_TOKEN -u GITHUB_TOKEN bash -c "${seg}"
		) >"${log}" 2>&1
	}

	local seg=""
	local idx=0
	local cand_fail_idx=-1
	local cand_fail_seg=""
	for seg in "${segments[@]}"; do
		if ! run_segment_in "${wt_path}" "${seg}" "${BASE_CHECK_DIR}/cand-${idx}.log"; then
			cand_fail_idx="${idx}"
			cand_fail_seg="${seg}"
			break
		fi
		idx=$((idx + 1))
	done

	local verdict="" substatus="" detail=""

	if [[ ${cand_fail_idx} -lt 0 ]]; then
		verdict="NO_FAILURE"
		substatus="NONE"
		detail="all ${#segments[@]} stage(s) pass in the candidate worktree; nothing to classify"
	else
		# One flake-retry before classifying: two of the five Jules CI_GATE failures
		# were unrelated flaky shards, which a retry catches without a base run.
		echo "[INFO] candidate failed stage ${cand_fail_idx}: ${cand_fail_seg}" >&2
		tail -n 15 "${BASE_CHECK_DIR}/cand-${cand_fail_idx}.log" >&2 || true
		if run_segment_in "${wt_path}" "${cand_fail_seg}" "${BASE_CHECK_DIR}/cand-retry.log"; then
			verdict="FLAKE_ON_RETRY"
			substatus="NONE"
			detail="stage ${cand_fail_idx} (${cand_fail_seg}) failed once then passed on retry; treated as a flake, not a regression"
		else
			local base_fail_idx=-1
			local base_fail_seg=""
			local bidx=0
			for seg in "${segments[@]}"; do
				if ! run_segment_in "${BASE_CHECK_WT}" "${seg}" "${BASE_CHECK_DIR}/base-${bidx}.log"; then
					base_fail_idx="${bidx}"
					base_fail_seg="${seg}"
					break
				fi
				bidx=$((bidx + 1))
			done

			if [[ ${base_fail_idx} -ge 0 ]]; then
				verdict="PRE_EXISTING_ON_BASE"
				substatus="PRE_EXISTING_FAILURE"
				detail="base_sha ${base_sha} also fails stage ${base_fail_idx} (${base_fail_seg}); candidate fails stage ${cand_fail_idx} (${cand_fail_seg}). Promote the candidate and file the base breakage separately."
				tail -n 15 "${BASE_CHECK_DIR}/base-${base_fail_idx}.log" >&2 || true
			else
				verdict="CAUSED_BY_CHANGE"
				substatus="GATE_FAILURE"
				detail="all ${#segments[@]} stage(s) pass at base_sha ${base_sha} but stage ${cand_fail_idx} (${cand_fail_seg}) fails in the candidate; this is a real regression, discard the candidate"
			fi
		fi
	fi

	echo "VERDICT: ${verdict}"
	echo "SUBSTATUS: ${substatus}"
	echo "REPO: abhimehro/${repo_name}"
	echo "BASE_SHA: ${base_sha}"
	echo "WORKTREE: ${wt_path}"
	echo "DETAIL: ${detail}"

	if [[ -n ${digest} ]]; then
		(
			umask 077
			{
				echo ""
				echo "## Base-Check Classification"
				echo ""
				echo "- Verdict: ${verdict}"
				echo "- Substatus: ${substatus}"
				echo "- Base SHA: ${base_sha}"
				echo "- Worktree: ${wt_path}"
				echo "- Detail: ${detail}"
			} >>"${digest}"
			chmod 600 "${digest}"
		)
		echo "DIGEST_UPDATED: ${digest}"
	fi

	if [[ ${verdict} == "CAUSED_BY_CHANGE" ]]; then
		exit 2
	fi
	return 0
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

	# Step 2/3: Remove only the global proactive skill symlinks that install created.
	# A user-managed symlink at the same path must survive rollback untouched.
	local skill=""
	local removed_skills=0
	for skill in "${SKILLS[@]}"; do
		local skill_link="${config_dir}/skills/${skill}"
		if [[ -L ${skill_link} ]] && [[ "$(readlink "${skill_link}")" == "${REPO_ROOT}/configs/antigravity/skills/${skill}" ]]; then
			rm -f "${skill_link}"
			removed_skills=$((removed_skills + 1))
		elif [[ -L ${skill_link} ]]; then
			echo "Step 2/3: skipped ${skill_link} (symlink not created by install; leaving in place)"
		fi
	done
	echo "Step 2/3: unlinked ${removed_skills} proactive skill symlinks"

	# Step 3/3: Unlink global hooks.json LAST, and only if install created the link.
	local hooks_link="${config_dir}/hooks.json"
	if [[ -L ${hooks_link} ]] && [[ "$(readlink "${hooks_link}")" != "${REPO_ROOT}/configs/antigravity/hooks.json" ]]; then
		echo "Step 3/3: skipped ${hooks_link} (symlink not created by install; leaving in place)"
	elif [[ -L ${hooks_link} ]]; then
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
	base-check)
		cmd_base_check "$@"
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
