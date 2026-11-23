#!/usr/bin/env bash
#
# Control and Ordered-Rollback Script for Antigravity Proactive Workflows.
# Manages copy-on-deploy skills, safety hook, and runtime scripts under
# $HOME/.gemini/config/proactive (decoupled from the repo working tree), chmod 700
# report and transcript permissions, staged sidecars (without ever self-enabling
# user_config.json), disposable timezone-aware cron canaries, verified
# post-merge Sentinel leases, MISSED slot auditing, and base-relative
# classification of verify failures so pre-existing breakage is never charged to
# the candidate.

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

ALL_PROACTIVE_REPOS=(
	"ctrld-sync"
	"email-security-pipeline"
	"personal-config"
	"Hydrograph_Versus_Seatek_Sensors_Project"
	"Seatek_Analysis"
	"series_correction_project_updated"
	"repoprompt-ce"
)

PILOT_SIDECAR_ID="proactive-pilot-ctrld-sync"
TRIAGE_SIDECAR_ID="proactive-pilot-triage"
CANARY_SIDECAR_ID="proactive-cron-canary"
PROACTIVE_MANAGED_MARKER=".managed-by-proactive-ctl"

RT_SKILLS_LINKED=0
RT_SKILLS_TOTAL="${#SKILLS[@]}"
RT_HOOKS_LINKED="no"
RT_HOOKS_MODE="absent"
RT_HOOKS_GUARD="missing"
RT_DANGLING_LINKS=0
RT_WORKTREE_SH=""
RT_CTL_SH=""
RT_GUARD_PY=""

is_research_repo() {
	local name="$1"
	case "${name}" in
	Hydrograph_Versus_Seatek_Sensors_Project | Seatek_Analysis | series_correction_project_updated)
		return 0
		;;
	*)
		return 1
		;;
	esac
}

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
  antigravity-proactive-ctl.sh install [--pilot] [--source-repo <dir>]
  antigravity-proactive-ctl.sh status
  antigravity-proactive-ctl.sh doctor [--fix] [--source-repo <dir>] [--repo <name> ...] [--all-repos] [--skip-fetch]
  antigravity-proactive-ctl.sh stage-repo --repo <name> [--cron "<expr>"] [--triage-cron "<expr>"] [--repo-path <dir>]
  antigravity-proactive-ctl.sh canary-stage [--offset-minutes <n>] [--timezone <iana_tz>]
  antigravity-proactive-ctl.sh canary-clean
  antigravity-proactive-ctl.sh sentinel-post-merge --repo <name> --pr <number>
  antigravity-proactive-ctl.sh audit-missed --date <YYYY-MM-DD> --repo <name>
  antigravity-proactive-ctl.sh sweep-date --cron "<expr>" [--now "<ISO-8601>"]
  antigravity-proactive-ctl.sh base-check --repo <name> --worktree <dir> [--digest <path>] [--test-cmd <cmd>]
  antigravity-proactive-ctl.sh disable

base-check exit codes:
  0 NO_FAILURE / FLAKE_ON_RETRY / PRE_EXISTING_ON_BASE (candidate promotable),
  1 usage, 2 CAUSED_BY_CHANGE (real regression, discard the candidate),
  6 could not create a pristine base worktree
EOF
}

require_flag_value() {
	local subcmd="$1"
	local flag="$2"
	local argc="$3"
	if [[ ${argc} -lt 2 ]]; then
		echo "[ERROR] ${subcmd}: ${flag} requires a value" >&2
		exit 1
	fi
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

file_sha256() {
	python3 - "$1" <<'PY'
import hashlib
import pathlib
import sys

print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
PY
}

atomic_install_file() {
	local mode="$1"
	local src="$2"
	local dst="$3"
	local tmp_dst="${dst}.tmp.$$"

	if [[ -d ${dst} ]] && [[ ! -L ${dst} ]]; then
		local invalid_backup=""
		invalid_backup="${dst}.invalid-dir.$(date -u +%Y%m%dT%H%M%SZ).$$"
		if ! mv "${dst}" "${invalid_backup}"; then
			echo "[ERROR] Cannot move directory out of managed file path ${dst}" >&2
			return 1
		fi
		echo "[WARN] Moved unexpected directory aside from ${dst} -> ${invalid_backup}" >&2
	fi

	install -m "${mode}" "${src}" "${tmp_dst}"
	if ! mv -f "${tmp_dst}" "${dst}"; then
		rm -f "${tmp_dst}"
		return 1
	fi
}

resolve_install_source_root() {
	local explicit_source="$1"
	local runtime_dir="$2"

	if [[ -n ${explicit_source} ]]; then
		if [[ ! -d ${explicit_source} ]]; then
			echo "[ERROR] install: --source-repo is not a directory: ${explicit_source}" >&2
			exit 1
		fi
		(cd "${explicit_source}" && pwd)
		return 0
	fi

	if [[ -f "${REPO_ROOT}/configs/antigravity/hooks/proactive-guard.py" ]]; then
		printf '%s' "${REPO_ROOT}"
		return 0
	fi

	if [[ -f "${runtime_dir}/.source-repo" ]]; then
		local recorded_root=""
		recorded_root="$(cat "${runtime_dir}/.source-repo" 2>/dev/null || true)"
		if [[ -n ${recorded_root} ]] && [[ -d ${recorded_root} ]] && [[ -f "${recorded_root}/configs/antigravity/hooks/proactive-guard.py" ]]; then
			printf '%s' "${recorded_root}"
			return 0
		fi
		echo "[ERROR] install: recorded checkout path is unavailable (${recorded_root:-empty}); pass --source-repo <personal-config-dir>" >&2
		exit 1
	fi

	echo "[ERROR] install requires a personal-config checkout (run from the repo or pass --source-repo <dir>)" >&2
	exit 1
}

resolve_legacy_repo_root() {
	local runtime_dir="$1"

	if [[ -f "${REPO_ROOT}/configs/antigravity/hooks.json" ]]; then
		printf '%s' "${REPO_ROOT}"
		return 0
	fi
	if [[ -f "${runtime_dir}/.source-repo" ]]; then
		cat "${runtime_dir}/.source-repo" 2>/dev/null || true
		return 0
	fi
}

validate_install_sources() {
	local source_root="$1"
	local stage_pilot="$2"

	local req_file=""
	for req_file in \
		"${source_root}/scripts/proactive-worktree.sh" \
		"${source_root}/scripts/antigravity-proactive-ctl.sh" \
		"${source_root}/configs/antigravity/hooks/proactive-guard.py" \
		"${source_root}/configs/antigravity/hooks.json"; do
		if [[ ! -f ${req_file} ]]; then
			echo "[ERROR] Missing installation source asset: ${req_file}" >&2
			exit 1
		fi
	done

	if ! python3 -m json.tool "${source_root}/configs/antigravity/hooks.json" >/dev/null 2>&1; then
		echo "[ERROR] Invalid JSON in source hooks.json: ${source_root}/configs/antigravity/hooks.json" >&2
		exit 1
	fi

	local skill=""
	for skill in "${SKILLS[@]}"; do
		local skill_src="${source_root}/configs/antigravity/skills/${skill}"
		if [[ ! -d ${skill_src} ]] || [[ ! -f "${skill_src}/SKILL.md" ]]; then
			echo "[ERROR] Missing skill source or SKILL.md: ${skill_src}" >&2
			exit 1
		fi
	done

	if [[ ${stage_pilot} -eq 1 ]]; then
		local sid=""
		for sid in "${PILOT_SIDECAR_ID}" "${TRIAGE_SIDECAR_ID}"; do
			local sidecar_src="${source_root}/configs/antigravity/sidecars/${sid}.sidecar.json"
			if [[ ! -f ${sidecar_src} ]]; then
				echo "[ERROR] Missing pilot sidecar template: ${sidecar_src}" >&2
				exit 1
			fi
			if ! python3 -m json.tool "${sidecar_src}" >/dev/null 2>&1; then
				echo "[ERROR] Invalid JSON in sidecar template: ${sidecar_src}" >&2
				exit 1
			fi
		done
	fi
}

deploy_runtime_files() {
	local source_root="$1"
	local runtime_dir="$2"
	local worktree_src="${source_root}/scripts/proactive-worktree.sh"
	local ctl_src="${source_root}/scripts/antigravity-proactive-ctl.sh"
	local guard_src="${source_root}/configs/antigravity/hooks/proactive-guard.py"

	mkdir -p "${runtime_dir}/scripts" "${runtime_dir}/hooks"
	chmod 700 "${runtime_dir}" "${runtime_dir}/scripts" "${runtime_dir}/hooks"
	atomic_install_file 755 "${worktree_src}" "${runtime_dir}/scripts/proactive-worktree.sh"
	atomic_install_file 755 "${ctl_src}" "${runtime_dir}/scripts/antigravity-proactive-ctl.sh"
	atomic_install_file 644 "${guard_src}" "${runtime_dir}/hooks/proactive-guard.py"

	local tmp_source="${runtime_dir}/.source-repo.tmp.$$"
	printf '%s\n' "${source_root}" >"${tmp_source}"
	chmod 600 "${tmp_source}"
	mv -f "${tmp_source}" "${runtime_dir}/.source-repo"
}

deploy_skill_dir() {
	local dst_dir="$1"
	local src_dir="$2"

	if [[ ! -d ${src_dir} ]]; then
		echo "[ERROR] Missing skill directory in repository: ${src_dir}" >&2
		exit 1
	fi

	# Stage the replacement completely before touching the live destination so
	# an interrupted copy never removes the working skill directory.
	local tmp_dir="${dst_dir}.tmp.$$"
	rm -rf "${tmp_dir}"
	mkdir -p "${tmp_dir}"
	if ! cp -R "${src_dir}/." "${tmp_dir}/"; then
		rm -rf "${tmp_dir}"
		echo "[ERROR] Failed to stage skill directory from ${src_dir} into ${tmp_dir}" >&2
		return 1
	fi
	printf 'managed\n' >"${tmp_dir}/${PROACTIVE_MANAGED_MARKER}"

	local old_dir=""
	local backup_dir=""
	if [[ -L ${dst_dir} ]]; then
		local link_target=""
		link_target="$(readlink "${dst_dir}" 2>/dev/null || true)"
		if [[ ${link_target} == "${src_dir}" ]]; then
			rm -f "${dst_dir}"
		else
			local backup_ts=""
			backup_ts="$(date -u +%Y%m%d_%H%M%S)"
			backup_dir="${dst_dir}.backup.${backup_ts}"
			mv "${dst_dir}" "${backup_dir}"
		fi
	elif [[ -e ${dst_dir} ]]; then
		if [[ -d ${dst_dir} ]] && [[ -f "${dst_dir}/${PROACTIVE_MANAGED_MARKER}" ]]; then
			old_dir="${dst_dir}.old.$$"
			rm -rf "${old_dir}"
			mv "${dst_dir}" "${old_dir}"
		else
			local backup_ts=""
			backup_ts="$(date -u +%Y%m%d_%H%M%S)"
			backup_dir="${dst_dir}.backup.${backup_ts}"
			mv "${dst_dir}" "${backup_dir}"
		fi
	fi

	if ! mv "${tmp_dir}" "${dst_dir}"; then
		if [[ -n ${old_dir} ]] && [[ -e ${old_dir} ]]; then
			mv "${old_dir}" "${dst_dir}" 2>/dev/null || true
		elif [[ -n ${backup_dir} ]] && { [[ -e ${backup_dir} ]] || [[ -L ${backup_dir} ]]; }; then
			mv "${backup_dir}" "${dst_dir}" 2>/dev/null || true
		fi
		rm -rf "${tmp_dir}"
		echo "ERROR: failed to move staged directory ${tmp_dir} into ${dst_dir}" >&2
		return 1
	fi
	if [[ -n ${old_dir} ]] && [[ -d ${old_dir} ]]; then
		rm -rf "${old_dir}"
	fi
}

is_hooks_file_managed() {
	local hooks_file="$1"
	local stamp_file="$2"
	local legacy_root="${3:-}"

	if [[ -L ${hooks_file} ]]; then
		[[ -n ${legacy_root} ]] && [[ "$(readlink "${hooks_file}")" == "${legacy_root}/configs/antigravity/hooks.json" ]]
		return $?
	fi

	if [[ ! -f ${hooks_file} ]] || [[ ! -f ${stamp_file} ]]; then
		return 1
	fi

	local current_hash=""
	local recorded_hash=""
	current_hash="$(file_sha256 "${hooks_file}" 2>/dev/null || true)"
	recorded_hash="$(cat "${stamp_file}" 2>/dev/null || true)"
	[[ -n ${current_hash} && ${current_hash} == "${recorded_hash}" ]]
}

deploy_hooks_file() {
	local dst_file="$1"
	local src_file="$2"
	local stamp_file="$3"
	local legacy_root="${4:-}"

	if [[ ! -f ${src_file} ]]; then
		echo "[ERROR] Missing hooks file in repository: ${src_file}" >&2
		exit 1
	fi

	if [[ -L ${dst_file} ]]; then
		rm -f "${dst_file}"
	elif [[ -f ${dst_file} ]] && ! is_hooks_file_managed "${dst_file}" "${stamp_file}" "${legacy_root}"; then
		local backup_ts=""
		backup_ts="$(date -u +%Y%m%d_%H%M%S)"
		mv "${dst_file}" "${dst_file}.backup.${backup_ts}"
	fi

	mkdir -p "$(dirname "${dst_file}")" "$(dirname "${stamp_file}")"
	atomic_install_file 600 "${src_file}" "${dst_file}"

	local tmp_stamp="${stamp_file}.tmp.$$"
	file_sha256 "${dst_file}" >"${tmp_stamp}"
	chmod 600 "${tmp_stamp}"
	mv -f "${tmp_stamp}" "${stamp_file}"
}

cmd_install() {
	local stage_pilot=0
	local explicit_source=""
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--pilot)
			stage_pilot=1
			shift
			;;
		--source-repo)
			require_flag_value "install" "$1" "$#"
			explicit_source="$2"
			shift 2
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
	local runtime_dir="${config_dir}/proactive"
	local reports_dir="${agy_dir}/proactive-reports"
	local worktrees_dir="${agy_dir}/worktrees"

	local source_root=""
	source_root="$(resolve_install_source_root "${explicit_source}" "${runtime_dir}")"
	validate_install_sources "${source_root}" "${stage_pilot}"

	mkdir -p "${skills_dir}" "${reports_dir}" "${worktrees_dir}"
	chmod 700 "${reports_dir}" "${worktrees_dir}"
	if [[ -d "${agy_dir}/brain" ]]; then
		chmod 700 "${agy_dir}/brain" 2>/dev/null || true
	fi
	if [[ -d ${cli_dir} ]]; then
		chmod 700 "${cli_dir}" 2>/dev/null || true
	fi

	deploy_runtime_files "${source_root}" "${runtime_dir}"

	local skill=""
	for skill in "${SKILLS[@]}"; do
		deploy_skill_dir \
			"${skills_dir}/${skill}" \
			"${source_root}/configs/antigravity/skills/${skill}"
	done

	deploy_hooks_file \
		"${config_dir}/hooks.json" \
		"${source_root}/configs/antigravity/hooks.json" \
		"${runtime_dir}/.hooks-managed" \
		"${source_root}"

	if [[ ${stage_pilot} -eq 1 ]]; then
		local sid=""
		for sid in "${PILOT_SIDECAR_ID}" "${TRIAGE_SIDECAR_ID}"; do
			local sidecar_src="${source_root}/configs/antigravity/sidecars/${sid}.sidecar.json"
			if [[ -f ${sidecar_src} ]]; then
				local sidecar_dir="${config_dir}/sidecars/${sid}"
				mkdir -p "${sidecar_dir}"
				python3 - "${sidecar_src}" "${sidecar_dir}/sidecar.json" "${HOME}" <<'PY'
import os
import pathlib
import sys

src = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
dst = pathlib.Path(sys.argv[2])
tmp = dst.with_name(f".{dst.name}.tmp.{os.getpid()}")
tmp.write_text(src.replace("__HOME__", sys.argv[3]), encoding="utf-8")
tmp.chmod(0o600)
os.replace(tmp, dst)
PY
			fi
		done
		# Never create or modify user_config.json; human enables in sidecar://dashboard.
	fi

	echo "Installed Antigravity proactive configuration (pilot_sidecar=${stage_pilot})"
}

report_sidecar_status() {
	local prefix="$1"
	local sidecar_id="$2"
	local config_dir="$3"
	local agy_dir="$4"

	local sidecar_file="${config_dir}/sidecars/${sidecar_id}/sidecar.json"
	local user_cfg="${config_dir}/sidecars/${sidecar_id}/user_config.json"
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
	local runtime_log="${agy_dir}/sidecar_data/${sidecar_id}/logs/sidecar.log"
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

	echo "${prefix}_sidecar=${sidecar_state}"
	echo "${prefix}_user_enabled=${enabled_state}"
	echo "${prefix}_runtime=${runtime_state}"
	echo "${prefix}_next_run=${next_run}"
}

report_exec_state() {
	local target_path="$1"
	if [[ -L ${target_path} ]] && [[ ! -e ${target_path} ]]; then
		printf 'broken-symlink'
	elif [[ -f ${target_path} ]] && [[ -x ${target_path} ]]; then
		printf 'ok'
	elif [[ -e ${target_path} ]] && [[ ! -f ${target_path} ]]; then
		printf 'invalid-type'
	elif [[ -f ${target_path} ]]; then
		printf 'not-executable'
	else
		printf 'missing'
	fi
}

report_file_state() {
	local target_path="$1"
	if [[ -L ${target_path} ]] && [[ ! -e ${target_path} ]]; then
		printf 'broken-symlink'
	elif [[ -f ${target_path} ]]; then
		printf 'ok'
	elif [[ -e ${target_path} ]] && [[ ! -f ${target_path} ]]; then
		printf 'invalid-type'
	else
		printf 'missing'
	fi
}

collect_runtime_health() {
	local config_dir="${HOME}/.gemini/config"
	local runtime_dir="${config_dir}/proactive"
	local linked=0
	local dangling_links=0
	local skill=""

	for skill in "${SKILLS[@]}"; do
		local skill_path="${config_dir}/skills/${skill}"
		if [[ -L ${skill_path} ]] && [[ ! -e ${skill_path} ]]; then
			dangling_links=$((dangling_links + 1))
		elif [[ -d ${skill_path} ]] && [[ -f "${skill_path}/SKILL.md" ]]; then
			linked=$((linked + 1))
		fi
	done

	local hooks_path="${config_dir}/hooks.json"
	local hooks_linked="no"
	local hooks_mode="absent"
	if [[ -L ${hooks_path} ]] && [[ ! -e ${hooks_path} ]]; then
		dangling_links=$((dangling_links + 1))
		hooks_mode="broken-symlink"
	elif [[ -L ${hooks_path} ]] && [[ -f ${hooks_path} ]]; then
		hooks_linked="yes"
		hooks_mode="symlink"
	elif [[ -f ${hooks_path} ]]; then
		hooks_linked="yes"
		hooks_mode="copy"
	fi

	local runtime_worktree_sh=""
	local runtime_ctl_sh=""
	local runtime_guard_py=""
	runtime_worktree_sh="$(report_exec_state "${runtime_dir}/scripts/proactive-worktree.sh")"
	runtime_ctl_sh="$(report_exec_state "${runtime_dir}/scripts/antigravity-proactive-ctl.sh")"
	runtime_guard_py="$(report_file_state "${runtime_dir}/hooks/proactive-guard.py")"

	local rt_state=""
	for rt_state in "${runtime_worktree_sh}" "${runtime_ctl_sh}" "${runtime_guard_py}"; do
		if [[ ${rt_state} == "broken-symlink" ]]; then
			dangling_links=$((dangling_links + 1))
		fi
	done

	local hooks_guard="missing"
	if [[ -f ${hooks_path} ]]; then
		hooks_guard="$(
			python3 - "${hooks_path}" <<'PY'
import json
import pathlib
import sys

try:
    with pathlib.Path(sys.argv[1]).open(encoding="utf-8") as handle:
        data = json.load(handle)
except Exception:
    print("invalid-json")
    sys.exit(0)

if not isinstance(data, dict):
    print("invalid-json")
    sys.exit(0)

guard = data.get("proactive-safety-guard")
if not isinstance(guard, dict) or guard.get("enabled") is not True:
    print("missing")
    sys.exit(0)

pre_tool = guard.get("PreToolUse")
if not isinstance(pre_tool, list):
    print("missing")
    sys.exit(0)

found = False
for entry in pre_tool:
    if not isinstance(entry, dict):
        continue
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        continue
    for hook in hooks:
        if isinstance(hook, dict) and hook.get("type") == "command":
            cmd = hook.get("command")
            if isinstance(cmd, str) and "proactive-guard.py" in cmd:
                found = True
                break
    if found:
        break

print("ok" if found else "missing")
PY
		)" || hooks_guard="missing"
	fi

	RT_SKILLS_LINKED="${linked}"
	RT_SKILLS_TOTAL="${#SKILLS[@]}"
	RT_HOOKS_LINKED="${hooks_linked}"
	RT_HOOKS_MODE="${hooks_mode}"
	RT_HOOKS_GUARD="${hooks_guard}"
	RT_DANGLING_LINKS="${dangling_links}"
	RT_WORKTREE_SH="${runtime_worktree_sh}"
	RT_CTL_SH="${runtime_ctl_sh}"
	RT_GUARD_PY="${runtime_guard_py}"
}

runtime_is_healthy() {
	[[ ${RT_SKILLS_LINKED} -eq ${RT_SKILLS_TOTAL} ]] &&
		[[ ${RT_HOOKS_LINKED} == "yes" ]] &&
		[[ ${RT_HOOKS_MODE} == "copy" ]] &&
		[[ ${RT_HOOKS_GUARD} == "ok" ]] &&
		[[ ${RT_DANGLING_LINKS} -eq 0 ]] &&
		[[ ${RT_WORKTREE_SH} == "ok" ]] &&
		[[ ${RT_CTL_SH} == "ok" ]] &&
		[[ ${RT_GUARD_PY} == "ok" ]]
}

print_runtime_health_fields() {
	echo "skills_linked=${RT_SKILLS_LINKED}/${RT_SKILLS_TOTAL}"
	echo "hooks_linked=${RT_HOOKS_LINKED}"
	echo "hooks_mode=${RT_HOOKS_MODE}"
	echo "hooks_guard=${RT_HOOKS_GUARD}"
	echo "dangling_links=${RT_DANGLING_LINKS}"
	echo "runtime_worktree_sh=${RT_WORKTREE_SH}"
	echo "runtime_ctl_sh=${RT_CTL_SH}"
	echo "runtime_guard_py=${RT_GUARD_PY}"
}

cmd_status() {
	local config_dir="${HOME}/.gemini/config"
	local agy_dir="${HOME}/.gemini/antigravity"

	collect_runtime_health

	local canary_state="absent"
	if [[ -f "${config_dir}/sidecars/${CANARY_SIDECAR_ID}/sidecar.json" ]]; then
		canary_state="present"
	fi

	print_runtime_health_fields
	report_sidecar_status "pilot" "${PILOT_SIDECAR_ID}" "${config_dir}" "${agy_dir}"
	report_sidecar_status "triage" "${TRIAGE_SIDECAR_ID}" "${config_dir}" "${agy_dir}"
	echo "canary_sidecar=${canary_state}"
	echo "reports_dir=${agy_dir}/proactive-reports"
}

cmd_doctor() {
	local fix_mode=0
	local source_repo=""
	local all_repos=0
	local skip_fetch=0
	local explicit_repos=()

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--fix)
			fix_mode=1
			shift
			;;
		--source-repo)
			require_flag_value "doctor" "$1" "$#"
			source_repo="$2"
			shift 2
			;;
		--repo)
			require_flag_value "doctor" "$1" "$#"
			local r_arg=""
			r_arg="${2##*/}"
			validate_repo_name "${r_arg}" "doctor"
			explicit_repos+=("${r_arg}")
			shift 2
			;;
		--all-repos)
			all_repos=1
			shift
			;;
		--skip-fetch)
			skip_fetch=1
			shift
			;;
		*)
			echo "[ERROR] Unknown flag for doctor: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ -n ${source_repo} ]] && [[ ! -d ${source_repo} ]]; then
		echo "[ERROR] doctor: --source-repo is not a directory: ${source_repo}" >&2
		exit 1
	fi

	local doctor_ok=1
	collect_runtime_health

	if ! runtime_is_healthy && [[ ${fix_mode} -eq 1 ]]; then
		local -a install_args=(--pilot)
		if [[ -n ${source_repo} ]]; then
			install_args+=(--source-repo "${source_repo}")
		fi
		if bash "${SCRIPT_DIR}/antigravity-proactive-ctl.sh" install "${install_args[@]}" >&2; then
			collect_runtime_health
			if runtime_is_healthy; then
				echo "auto_healed_install=yes"
			else
				echo "auto_healed_install=failed"
			fi
		else
			echo "auto_healed_install=failed"
		fi
	fi

	if runtime_is_healthy; then
		echo "runtime_health=ok"
	else
		echo "runtime_health=degraded"
		doctor_ok=0
	fi
	print_runtime_health_fields

	local worktree_sh=""
	if [[ -x "${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh" ]]; then
		worktree_sh="${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh"
	else
		worktree_sh="${SCRIPT_DIR}/proactive-worktree.sh"
	fi

	if [[ ! -x ${worktree_sh} ]]; then
		echo "[ERROR] doctor: proactive-worktree.sh not found or not executable: ${worktree_sh}" >&2
		echo "doctor_status=DEGRADED"
		exit 1
	fi

	local target_repos=()
	if [[ ${#explicit_repos[@]} -gt 0 ]]; then
		target_repos=("${explicit_repos[@]}")
	elif [[ ${all_repos} -eq 1 ]]; then
		target_repos=("${ALL_PROACTIVE_REPOS[@]}")
	else
		target_repos=("ctrld-sync")
	fi

	local r=""
	for r in "${target_repos[@]}"; do
		local repo_dir="${HOME}/dev/${r}"
		if [[ ! -d ${repo_dir} ]] || { [[ ! -e "${repo_dir}/.git" ]] && ! git -C "${repo_dir}" rev-parse --git-dir >/dev/null 2>&1; }; then
			echo "repo_${r}=MISSING_REPO"
			doctor_ok=0
			continue
		fi

		local -a preflight_args=(
			preflight
			--repo "abhimehro/${r}"
			--repo-path "${repo_dir}"
		)
		if [[ ${fix_mode} -eq 1 ]]; then
			preflight_args+=(--auto-heal)
		fi
		if [[ ${skip_fetch} -eq 1 ]]; then
			preflight_args+=(--skip-fetch)
		fi

		local pf_out=""
		local pf_rc=0
		pf_out="$("${worktree_sh}" "${preflight_args[@]}" 2>&1)" || pf_rc=$?

		local repo_status=""
		case "${pf_rc}" in
		0)
			repo_status="PASS"
			;;
		6)
			if printf '%s\n' "${pf_out}" | grep -qE '^git_fetch=failed$'; then
				repo_status="FAIL_FETCH"
			else
				repo_status="FAIL_AUTH"
			fi
			doctor_ok=0
			;;
		7)
			repo_status="FAIL_TOOLCHAIN"
			doctor_ok=0
			;;
		*)
			repo_status="FAIL_ERROR"
			doctor_ok=0
			;;
		esac

		echo "repo_${r}=${repo_status}"
		if [[ ${pf_rc} -eq 7 ]]; then
			local rem_line=""
			rem_line="$(printf '%s\n' "${pf_out}" | grep -E '^remediation=' | head -n 1 || true)"
			if [[ -n ${rem_line} ]]; then
				echo "repo_${r}_remediation=${rem_line#remediation=}"
			fi
		fi
		if [[ ${pf_rc} -ne 0 ]] && [[ -n ${pf_out} ]]; then
			printf '[doctor:%s] %s\n' "${r}" "${pf_out}" >&2
		fi
	done

	if [[ ${doctor_ok} -eq 1 ]]; then
		echo "doctor_status=HEALTHY"
		return 0
	fi
	echo "doctor_status=DEGRADED"
	exit 1
}

cmd_stage_repo() {
	local repo_name=""
	local sweep_cron="CRON_TZ=America/Chicago 15 8 * * 1-5"
	local triage_cron="CRON_TZ=America/Chicago 35 8 * * 1-5"
	local repo_path=""

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--repo)
			require_flag_value "stage-repo" "$1" "$#"
			repo_name="${2##*/}"
			shift 2
			;;
		--cron)
			require_flag_value "stage-repo" "$1" "$#"
			sweep_cron="$2"
			shift 2
			;;
		--triage-cron)
			require_flag_value "stage-repo" "$1" "$#"
			triage_cron="$2"
			shift 2
			;;
		--repo-path)
			require_flag_value "stage-repo" "$1" "$#"
			repo_path="$2"
			shift 2
			;;
		*)
			echo "[ERROR] Unknown flag for stage-repo: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ -z ${repo_name} ]]; then
		echo "[ERROR] stage-repo requires --repo <name>" >&2
		exit 1
	fi
	validate_repo_name "${repo_name}" "stage-repo"
	if [[ -z ${sweep_cron} ]] || [[ -z ${triage_cron} ]]; then
		echo "[ERROR] stage-repo requires non-empty --cron and --triage-cron values" >&2
		exit 1
	fi
	if [[ -z ${repo_path} ]]; then
		repo_path="__HOME__/dev/${repo_name}"
	fi

	local repo_kind="core"
	if is_research_repo "${repo_name}"; then
		repo_kind="research"
	fi

	local config_dir="${HOME}/.gemini/config"
	local sweep_dir="${config_dir}/sidecars/proactive-sweep-${repo_name}"
	local triage_dir="${config_dir}/sidecars/proactive-triage-${repo_name}"
	mkdir -p "${sweep_dir}" "${triage_dir}"

	python3 - "${sweep_dir}/sidecar.json" "${triage_dir}/sidecar.json" "${HOME}" "${repo_name}" "${repo_path}" "${repo_kind}" "${sweep_cron}" "${triage_cron}" <<'PY'
import json
import os
import pathlib
import shlex
import sys

sweep_path = pathlib.Path(sys.argv[1])
triage_path = pathlib.Path(sys.argv[2])
home_dir = sys.argv[3]
repo_name = sys.argv[4]
repo_path = sys.argv[5].replace("__HOME__", home_dir)
repo_kind = sys.argv[6]
sweep_cron = sys.argv[7]
triage_cron = sys.argv[8]

marker = ".gemini/config/proactive/scripts/"
for existing_path in (sweep_path, triage_path):
    if existing_path.is_symlink():
        sys.stderr.write(
            f"[ERROR] Refusing to overwrite symlinked sidecar: {existing_path}\n"
        )
        sys.exit(1)
    if existing_path.exists():
        if not existing_path.is_file():
            sys.stderr.write(
                f"[ERROR] Refusing to overwrite non-file sidecar path: {existing_path}\n"
            )
            sys.exit(1)
        if marker not in existing_path.read_text(encoding="utf-8", errors="replace"):
            sys.stderr.write(
                f"[ERROR] Refusing to overwrite non-managed custom sidecar: {existing_path}\n"
            )
            sys.exit(1)

worktree_sh = f"{home_dir}/.gemini/config/proactive/scripts/proactive-worktree.sh"
ctl_sh = f"{home_dir}/.gemini/config/proactive/scripts/antigravity-proactive-ctl.sh"
reports_dir = f"{home_dir}/.gemini/antigravity/proactive-reports"
worktrees_dir = f"{home_dir}/.gemini/antigravity/worktrees"
skills_dir = f"{home_dir}/.gemini/config/skills"
quoted_cron = shlex.quote(sweep_cron)

if repo_kind == "research":
    lens_guidance = (
        "rotating code-health and bolt lenses across weekdays, plus a read-only "
        "sentinel check; NEVER run palette on this scientific research repository"
    )
    verify_guidance = (
        "verify via verify --worktree <wt_path> --lens <lens> "
        "(passing mandatory --numeric-check-cmd tolerance verification whenever lens is bolt)"
    )
else:
    lens_guidance = (
        "rotating bolt, code-health, and palette lenses across weekdays, "
        "plus a read-only sentinel check"
    )
    verify_guidance = "verify via verify --worktree <wt_path> --lens <lens>"

sweep_prompt = (
    f"[PROACTIVE-SWEEP] Run /proactive-repo-sweep on {repo_path} "
    f"(GitHub repo abhimehro/{repo_name}) in strict local-only mode (2B). "
    f"Time-box this run to 15 minutes and produce at most 1 verified improvement ({lens_guidance}). "
    f"Read {repo_path}/AGENTS.md (and {repo_path}/.jules/ journals if present) first, "
    f"run Step 0 {worktree_sh} preflight --repo abhimehro/{repo_name} --repo-path {repo_path} --auto-heal, "
    f"then run {worktree_sh} cleanup --ttl-days 21 and check-throttle --repo abhimehro/{repo_name} "
    f"--include-worktrees --repo-path {repo_path}, check open-PR file collisions via check-collisions "
    f"before editing, prepare an isolated local worktree via prepare --repo abhimehro/{repo_name} "
    f"--repo-path {repo_path} --lens <lens> --mode local, "
    f"{verify_guidance} without modifying build, lock, script, or test harnesses, "
    "and if verify reports a semantic test-coverage BLOCK restore the lost coverage rather than deleting "
    "tests or pinning --expected-test-count, resolve SWEEP_DATE via "
    f"`{ctl_sh} sweep-date --cron {quoted_cron}`, and write a chmod 600 digest report to "
    f"{reports_dir}/$SWEEP_DATE-{repo_name}.md. Do not push branches, open PRs, or edit .jules/sentinel.md."
)

triage_prompt = (
    f"[PROACTIVE-TRIAGE] Post-sweep review for {repo_name} (2B, human-in-the-loop). "
    "Do NOT push, open PRs, or re-run the sweep. Steps: "
    f"(1) Resolve SWEEP_DATE via `{ctl_sh} sweep-date --cron {quoted_cron}` and read {reports_dir}/$SWEEP_DATE-{repo_name}.md. "
    f"(2) If no digest exists, run `{ctl_sh} audit-missed --date \"$SWEEP_DATE\" --repo {repo_name} --cron {quoted_cron}` once, "
    "record Status MISSED in the summary, and do NOT retry or start a run. "
    "(3) Otherwise inspect the referenced worktree (git diff --shortstat vs base_sha) and re-check verify exit status from the digest. "
    f"(3b) If verify did not exit 0, run `{ctl_sh} base-check --repo {repo_name} --worktree <worktree_path> --digest <digest_path>` ONCE "
    "and report its VERDICT line: FLAKE_ON_RETRY or PRE_EXISTING_ON_BASE (exit 0) means the candidate is still promotable "
    "and any base breakage is filed separately, while CAUSED_BY_CHANGE (exit 2) means discard the candidate. "
    "Never re-run the sweep to fix a failure that base-check attributes to base. "
    "(4) Post a TIGHT summary to the user with exactly these fields: repo, Status, "
    "Substatus (NONE|FLOAT_REORDER_DRIFT|GATE_FAILURE|PRE_EXISTING_FAILURE), base-check Verdict when it ran, "
    "verify exit code, diff size (files/+/-), and a one-line call: 'worth a look' or 'skip'. "
    "Never print secrets or sentinel details beyond the Status and a pointer to the local digest path. "
    "Sentinel stays local-only (SECURITY_REPORT_ONLY), never staged for a public PR."
)

sweep_doc = {
    "builtin": "schedule",
    "args": [sweep_cron, "agentapi", "new-conversation", "--", sweep_prompt],
    "restart_policy": "always",
    "display_name": f"Proactive Sweep ({repo_name})",
    "description": (
        f"Scheduled ({sweep_cron}) isolated local-only proactive sweep on {repo_name} "
        f"({repo_kind}) ahead of the PR lifecycle."
    ),
    "agent_permissions": {
        "allows_user_interactions": False,
        "workspace_uris": [f"file://{worktrees_dir}"],
        "access_grants": [
            f"read_file({repo_path})",
            f"read_file({skills_dir})",
            f"read_file({reports_dir})",
            f"write_file({reports_dir})",
            f"write_file({worktrees_dir})",
            f"command({home_dir}/bin/agent-zsh -c)",
            f"command({worktree_sh})",
            f"command({ctl_sh} sweep-date)",
            "command(gh pr list)",
            "command(gh auth status)",
            "command(git -C)",
        ],
    },
}

triage_doc = {
    "builtin": "schedule",
    "args": [triage_cron, "agentapi", "new-conversation", "--", triage_prompt],
    "restart_policy": "always",
    "display_name": f"Proactive Triage Review ({repo_name})",
    "description": (
        f"Scheduled ({triage_cron}) post-sweep review for {repo_name}; "
        "inspects the proactive digest and outputs a tight triage summary."
    ),
    "agent_permissions": {
        "allows_user_interactions": True,
        "workspace_uris": [f"file://{reports_dir}"],
        "access_grants": [
            f"read_file({reports_dir})",
            f"write_file({reports_dir})",
            f"read_file({worktrees_dir})",
            f"write_file({worktrees_dir})",
            f"command({home_dir}/bin/agent-zsh -c)",
            f"command({ctl_sh} sweep-date)",
            f"command({ctl_sh} audit-missed)",
            f"command({ctl_sh} base-check)",
            f"command({ctl_sh} doctor)",
            "command(git -C)",
        ],
    },
}


def atomic_write_0600(dst: pathlib.Path, doc: dict) -> None:
    tmp = dst.with_name(f".{dst.name}.tmp.{os.getpid()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(doc, indent=2) + "\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, dst)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


atomic_write_0600(sweep_path, sweep_doc)
atomic_write_0600(triage_path, triage_doc)
PY

	echo "Staged proactive-sweep-${repo_name} (${repo_kind}) at ${sweep_dir}/sidecar.json"
	echo "Staged proactive-triage-${repo_name} (${repo_kind}) at ${triage_dir}/sidecar.json"
}

cmd_canary_stage() {
	local offset_min=4
	local tz_name="America/Chicago"
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--offset-minutes)
			require_flag_value "canary-stage" "$1" "$#"
			offset_min="$2"
			shift 2
			;;
		--timezone | --tz)
			require_flag_value "canary-stage" "$1" "$#"
			tz_name="$2"
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

	python3 - "${canary_dir}/sidecar.json" "${reports_dir}" "${offset_min}" "${HOME}" "${tz_name}" <<'PY'
import datetime as dt
import json
import os
import pathlib
import re
import sys
import zoneinfo

out_path = pathlib.Path(sys.argv[1])
reports_dir = sys.argv[2]
raw_offset = sys.argv[3]
home_dir = sys.argv[4]
tz_name = sys.argv[5]

try:
    offset = int(raw_offset)
except ValueError:
    sys.stderr.write(f"[ERROR] canary-stage --offset-minutes must be an integer, got: {raw_offset}\n")
    sys.exit(1)
if offset < 1:
    sys.stderr.write(f"[ERROR] canary-stage --offset-minutes must be >= 1, got: {offset}\n")
    sys.exit(1)

# tz_name is interpolated into cron_expr, receipt filename, and the shell command.
if not re.fullmatch(r"[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*", tz_name) or ".." in tz_name.split("/"):
    sys.stderr.write(f"[ERROR] canary-stage invalid --timezone name: {tz_name}\n")
    sys.exit(1)
try:
    zone = zoneinfo.ZoneInfo(tz_name)
except zoneinfo.ZoneInfoNotFoundError:
    sys.stderr.write(f"[ERROR] canary-stage unknown IANA timezone: {tz_name}\n")
    sys.exit(1)

now_override = os.environ.get("PROACTIVE_CANARY_NOW_UTC", "").strip()
if now_override:
    try:
        now_utc = dt.datetime.fromisoformat(now_override.replace("Z", "+00:00"))
    except ValueError:
        sys.stderr.write(f"[ERROR] canary-stage invalid PROACTIVE_CANARY_NOW_UTC: {now_override}\n")
        sys.exit(1)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=dt.timezone.utc)
    else:
        now_utc = now_utc.astimezone(dt.timezone.utc)
else:
    now_utc = dt.datetime.now(dt.timezone.utc)

# Convert fire_utc into the target zone rather than merely relabelling CRON_TZ;
# otherwise an America/Chicago canary stages a UTC wall-clock hour and silently misfires.
fire_utc = now_utc + dt.timedelta(minutes=offset)
fire_local = fire_utc.astimezone(zone)
cron_expr = (
    f"CRON_TZ={tz_name} "
    f"{fire_local.minute} {fire_local.hour} {fire_local.day} {fire_local.month} *"
)
safe_tz = re.sub(r"[^A-Za-z0-9._-]+", "-", tz_name).strip("-").lower()
receipt_path = f"{reports_dir}/canary-{safe_tz}-receipt.md"
local_render = fire_local.strftime("%Y-%m-%d %H:%M %Z")
utc_render = fire_utc.strftime("%Y-%m-%d %H:%M UTC")

shell_cmd = (
    "umask 077 && { "
    f'TZ={tz_name} date +"CANARY_TIMEZONE={tz_name} CANARY_FIRED_LOCAL=%Y-%m-%dT%H:%M:%S%z"; '
    'date -u +"CANARY_FIRED_UTC=%Y-%m-%dT%H:%M:%SZ"; '
    f'}} > "{receipt_path}"'
)

doc = {
    "builtin": "schedule",
    "args": [
        cron_expr,
        "agentapi",
        "new-conversation",
        "--",
        f"[PROACTIVE-SWEEP] Disposable cron canary check (timezone={tz_name}). "
        f"Run `{home_dir}/bin/agent-zsh -c '{shell_cmd}'` "
        "and reply ONLY with `CANARY_OK`.",
    ],
    "restart_policy": "always",
    "display_name": "Proactive Cron Canary (Disposable)",
    "description": (
        f"One-time disposable cron test ({tz_name}) scheduled for {local_render} ({utc_render}). "
        "Remove afterward via antigravity-proactive-ctl.sh canary-clean."
    ),
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
print(
    f"Staged disposable canary [{tz_name}] for {local_render} ({utc_render}) ({cron_expr}); "
    f"receipt={receipt_path}"
)
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
			require_flag_value "sentinel-post-merge" "$1" "$#"
			repo_name="${2##*/}"
			shift 2
			;;
		--pr)
			require_flag_value "sentinel-post-merge" "$1" "$#"
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
	local cron_expr="CRON_TZ=America/Chicago 15 8 * * 1-5"
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--date)
			require_flag_value "audit-missed" "$1" "$#"
			date_str="$2"
			shift 2
			;;
		--repo)
			require_flag_value "audit-missed" "$1" "$#"
			repo_name="${2##*/}"
			shift 2
			;;
		--cron)
			require_flag_value "audit-missed" "$1" "$#"
			cron_expr="$2"
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

	# Resolve the scheduled slot description from the cron expression (defaulting to
	# 08:15 America/Chicago) and validate the calendar date + timezone.
	local slot_desc=""
	if ! slot_desc="$(
		python3 - "${date_str}" "${cron_expr}" <<'PY'
import datetime
import sys
import zoneinfo

day = datetime.date.fromisoformat(sys.argv[1])
cron_expr = sys.argv[2].strip()
tokens = cron_expr.split()
tz_name = "UTC"
while tokens and (tokens[0].startswith("CRON_TZ=") or tokens[0].startswith("TZ=")):
    tz_name = tokens.pop(0).split("=", 1)[1].strip() or "UTC"

if len(tokens) < 5:
    sys.stderr.write(f"[ERROR] audit-missed: invalid cron expression: {cron_expr}\n")
    sys.exit(2)

zone = zoneinfo.ZoneInfo(tz_name)
min_f, hour_f = tokens[0], tokens[1]
if min_f.isdigit() and hour_f.isdigit():
    minute = int(min_f)
    hour = int(hour_f)
    if not (0 <= minute <= 59 and 0 <= hour <= 23):
        sys.stderr.write(f"[ERROR] audit-missed: invalid hour/minute in cron: {cron_expr}\n")
        sys.exit(2)
    local = datetime.datetime.combine(day, datetime.time(hour, minute), tzinfo=zone)
    utc_hm = local.astimezone(datetime.timezone.utc).strftime("%H:%M")
    if tz_name == "UTC":
        print(f"{day.isoformat()} {hour:02d}:{minute:02d} UTC")
    else:
        print(f"{day.isoformat()} {hour:02d}:{minute:02d} {tz_name} ({utc_hm} UTC)")
else:
    print(f"{day.isoformat()} ({cron_expr})")
PY
	)"; then
		echo "[ERROR] audit-missed invalid --date or --cron: date=${date_str} cron=${cron_expr}" >&2
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
- Scheduled Slot: ${slot_desc}
- Reason: No digest recorded for this scheduled slot (host asleep, Antigravity.app closed, or sidecar disabled). Excluded from mergeable-rate denominator.
EOF
		chmod 600 "${report_file}"
	)
	echo "MISSED_RECORDED: ${report_file}"
}

cmd_sweep_date() {
	local cron_expr=""
	local now_str=""

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--cron)
			require_flag_value "sweep-date" "$1" "$#"
			cron_expr="$2"
			shift 2
			;;
		--now)
			require_flag_value "sweep-date" "$1" "$#"
			now_str="$2"
			shift 2
			;;
		*)
			echo "[ERROR] Unknown flag for sweep-date: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ -z ${cron_expr} ]]; then
		echo '[ERROR] sweep-date requires --cron "<expr>"' >&2
		exit 1
	fi

	python3 - "${cron_expr}" "${now_str}" <<'PY'
import datetime as dt
import sys
import zoneinfo

cron_expr = sys.argv[1].strip()
now_raw = sys.argv[2].strip()

tokens = cron_expr.split()
tz_name = "UTC"
while tokens and (tokens[0].startswith("CRON_TZ=") or tokens[0].startswith("TZ=")):
    tz_name = tokens.pop(0).split("=", 1)[1].strip() or "UTC"

if len(tokens) < 5:
    sys.stderr.write(f"[ERROR] sweep-date: invalid cron expression: {cron_expr}\n")
    sys.exit(1)

try:
    zone = zoneinfo.ZoneInfo(tz_name)
except zoneinfo.ZoneInfoNotFoundError:
    sys.stderr.write(f"[ERROR] sweep-date: unknown timezone in cron expression: {tz_name}\n")
    sys.exit(1)

if now_raw:
    try:
        now_dt = dt.datetime.fromisoformat(now_raw.replace("Z", "+00:00"))
    except ValueError:
        sys.stderr.write(f"[ERROR] sweep-date: invalid --now timestamp: {now_raw}\n")
        sys.exit(1)
    if now_dt.tzinfo is None:
        now_utc = now_dt.replace(tzinfo=dt.timezone.utc)
    else:
        now_utc = now_dt.astimezone(dt.timezone.utc)
else:
    now_utc = dt.datetime.now(dt.timezone.utc)

MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
DOW_NAMES = {
    "sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6,
}


def parse_cron_atom(token, min_val, max_val, names=None):
    low = token.strip().lower()
    if names and low in names:
        return names[low]
    val = int(low)
    if val < min_val or val > max_val:
        raise ValueError(f"out of range {min_val}..{max_val}: {token}")
    return val


def parse_cron_field(expr, min_val, max_val, names=None, is_dow=False):
    result = set()
    for part in expr.split(","):
        if not part:
            raise ValueError(f"empty item in cron field: {expr}")
        if "/" in part:
            range_part, step_str = part.split("/", 1)
            step = int(step_str)
            if step <= 0:
                raise ValueError(f"non-positive step in cron field: {expr}")
        else:
            range_part, step = part, 1

        if range_part == "*":
            start, end = min_val, max_val
        elif "-" in range_part:
            a_str, b_str = range_part.split("-", 1)
            start = parse_cron_atom(a_str, min_val, max_val, names)
            end = parse_cron_atom(b_str, min_val, max_val, names)
            if start > end:
                raise ValueError(f"descending range in cron field: {expr}")
        else:
            start = parse_cron_atom(range_part, min_val, max_val, names)
            end = max_val if "/" in part else start

        for v in range(start, end + 1, step):
            result.add(0 if (is_dow and v == 7) else v)

    if not result:
        raise ValueError(f"empty match set for cron field: {expr}")
    return result


min_f, hour_f, dom_f, month_f, dow_f = tokens[:5]
try:
    minutes = sorted(parse_cron_field(min_f, 0, 59), reverse=True)
    hours = sorted(parse_cron_field(hour_f, 0, 23), reverse=True)
    dom_set = parse_cron_field(dom_f, 1, 31)
    month_set = parse_cron_field(month_f, 1, 12, names=MONTH_NAMES)
    dow_set = parse_cron_field(dow_f, 0, 7, names=DOW_NAMES, is_dow=True)
except ValueError as exc:
    sys.stderr.write(f"[ERROR] sweep-date: invalid cron expression '{cron_expr}': {exc}\n")
    sys.exit(1)

dom_restricted = dom_f != "*"
dow_restricted = dow_f != "*"
now_local = now_utc.astimezone(zone)

best_utc = None
for day_offset in range(-1, 371):
    cand_date = now_local.date() - dt.timedelta(days=day_offset)
    if cand_date.month not in month_set:
        continue
    cron_dow = (cand_date.weekday() + 1) % 7
    dom_ok = cand_date.day in dom_set
    dow_ok = cron_dow in dow_set
    day_ok = (dom_ok or dow_ok) if (dom_restricted and dow_restricted) else (dom_ok and dow_ok)
    if not day_ok:
        continue

    day_best = None
    for h in hours:
        for m in minutes:
            cand_naive = dt.datetime.combine(cand_date, dt.time(h, m))
            for fold in (1, 0):
                cand_local = cand_naive.replace(tzinfo=zone, fold=fold)
                cand_utc = cand_local.astimezone(dt.timezone.utc)
                if cand_utc.astimezone(zone).replace(tzinfo=None) != cand_naive:
                    continue
                if cand_utc <= now_utc and (day_best is None or cand_utc > day_best):
                    day_best = cand_utc
    if day_best is not None and (best_utc is None or day_best > best_utc):
        best_utc = day_best
        break

if best_utc is None:
    sys.stderr.write(
        f"[ERROR] sweep-date: no scheduled slot found within 370 days for '{cron_expr}'\n"
    )
    sys.exit(1)

print(best_utc.strftime("%Y-%m-%d"))
PY
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
			require_flag_value "base-check" "$1" "$#"
			repo_name="${2##*/}"
			shift 2
			;;
		--worktree)
			require_flag_value "base-check" "$1" "$#"
			wt_path="$2"
			shift 2
			;;
		--digest)
			require_flag_value "base-check" "$1" "$#"
			digest="$2"
			shift 2
			;;
		--test-cmd)
			require_flag_value "base-check" "$1" "$#"
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

	local meta_repo="" base_sha="" repo_path=""
	meta_repo="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("repo_name") or "")' "${meta_file}" 2>/dev/null || true)"
	base_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("base_sha") or "")' "${meta_file}" 2>/dev/null || true)"
	repo_path="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("repo_path") or "")' "${meta_file}" 2>/dev/null || true)"
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
	# not pass because the ambient environment can reach a remote. Non-uv stages
	# also auto-resolve the repo or worktree .venv/bin and strip ambient VIRTUAL_ENV.
	run_segment_in() {
		local dir="$1"
		local seg="$2"
		local log="$3"
		local fallback_repo="${4:-}"
		local seg_path="${PATH}"
		local seg_pythonpath="${PYTHONPATH:-}"
		if [[ ${seg} != *"uv run"* ]]; then
			if [[ -d "${dir%/}/.venv/bin" ]]; then
				seg_path="${dir%/}/.venv/bin:${PATH}"
			elif [[ -n ${fallback_repo} ]] && [[ -d "${fallback_repo%/}/.venv/bin" ]]; then
				seg_path="${fallback_repo%/}/.venv/bin:${PATH}"
				seg_pythonpath="${dir%/}${seg_pythonpath:+:${seg_pythonpath}}"
			fi
		fi
		(
			cd "${dir}" || exit 1
			if [[ -n ${seg_pythonpath} ]]; then
				PATH="${seg_path}" PYTHONPATH="${seg_pythonpath}" env -u SSH_AUTH_SOCK -u GH_TOKEN -u GITHUB_TOKEN -u VIRTUAL_ENV bash -c "${seg}"
			else
				PATH="${seg_path}" env -u SSH_AUTH_SOCK -u GH_TOKEN -u GITHUB_TOKEN -u VIRTUAL_ENV bash -c "${seg}"
			fi
		) >"${log}" 2>&1
	}

	local seg=""
	local idx=0
	local cand_fail_idx=-1
	local cand_fail_seg=""
	for seg in "${segments[@]}"; do
		if ! run_segment_in "${wt_path}" "${seg}" "${BASE_CHECK_DIR}/cand-${idx}.log" "${repo_path}"; then
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
		if run_segment_in "${wt_path}" "${cand_fail_seg}" "${BASE_CHECK_DIR}/cand-retry.log" "${repo_path}"; then
			verdict="FLAKE_ON_RETRY"
			substatus="NONE"
			detail="stage ${cand_fail_idx} (${cand_fail_seg}) failed once then passed on retry; treated as a flake, not a regression"
		else
			local base_fail_idx=-1
			local base_fail_seg=""
			local bidx=0
			for seg in "${segments[@]}"; do
				if ! run_segment_in "${BASE_CHECK_WT}" "${seg}" "${BASE_CHECK_DIR}/base-${bidx}.log" "${repo_path}"; then
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

sanitize_restored_hooks() {
	local hooks_file="$1"

	python3 - "${hooks_file}" <<'PY'
import json
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
raw = path.read_text(encoding="utf-8", errors="replace")
marker = ".gemini/config/proactive"


def contains_marker(obj: object) -> bool:
    if isinstance(obj, str):
        return marker in obj
    if isinstance(obj, dict):
        return any(contains_marker(k) or contains_marker(v) for k, v in obj.items())
    if isinstance(obj, list):
        return any(contains_marker(item) for item in obj)
    return False


try:
    data = json.loads(raw)
except json.JSONDecodeError:
    sys.exit(11)

if not isinstance(data, dict):
    sys.exit(11)

if not contains_marker(data):
    sys.exit(0)

if "proactive-safety-guard" in data:
    data.pop("proactive-safety-guard", None)
    rendered = json.dumps(data, indent=2) + "\n"
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(rendered, encoding="utf-8")
    tmp.chmod(0o600)
    os.replace(tmp, path)
    if contains_marker(data):
        sys.exit(10)
    sys.exit(0)

sys.exit(10)
PY
}

cmd_disable() {
	local config_dir="${HOME}/.gemini/config"
	local runtime_dir="${config_dir}/proactive"
	local stamp_file="${runtime_dir}/.hooks-managed"
	local legacy_root=""
	legacy_root="$(resolve_legacy_repo_root "${runtime_dir}")"

	# Step 1/3: Stop/remove sidecars FIRST so no scheduled sweep can fire unguarded.
	local sid=""
	for sid in "${PILOT_SIDECAR_ID}" "${TRIAGE_SIDECAR_ID}" "${CANARY_SIDECAR_ID}"; do
		local sidecar_dir="${config_dir}/sidecars/${sid}"
		rm -f "${sidecar_dir}/sidecar.json" "${sidecar_dir}/user_config.json"
		rmdir "${sidecar_dir}" 2>/dev/null || true
	done
	local dyn_dir=""
	for dyn_dir in "${config_dir}/sidecars"/proactive-sweep-* "${config_dir}/sidecars"/proactive-triage-*; do
		[[ ! -L ${dyn_dir} ]] && [[ -d ${dyn_dir} ]] || continue
		local dyn_sidecar="${dyn_dir}/sidecar.json"
		if [[ ! -L ${dyn_sidecar} ]] && [[ -f ${dyn_sidecar} ]] && grep -qF '.gemini/config/proactive/scripts/' "${dyn_sidecar}" 2>/dev/null; then
			rm -f "${dyn_sidecar}" "${dyn_dir}/user_config.json"
			rmdir "${dyn_dir}" 2>/dev/null || true
		fi
	done
	echo "Step 1/3: removed sidecar definitions before removing safety hooks"

	# Step 2/3: Remove only the proactive skill symlinks/copies that install created.
	# User-managed symlinks or unmanaged directories at the same path must survive rollback.
	local skill=""
	local removed_skills=0
	for skill in "${SKILLS[@]}"; do
		local skill_path="${config_dir}/skills/${skill}"
		if [[ -L ${skill_path} ]] && [[ -n ${legacy_root} ]] && [[ "$(readlink "${skill_path}")" == "${legacy_root}/configs/antigravity/skills/${skill}" ]]; then
			rm -f "${skill_path}"
			removed_skills=$((removed_skills + 1))
		elif [[ -L ${skill_path} ]]; then
			echo "Step 2/3: skipped ${skill_path} (symlink not created by install; leaving in place)"
		elif [[ -d ${skill_path} ]] && [[ -f "${skill_path}/${PROACTIVE_MANAGED_MARKER}" ]]; then
			rm -rf "${skill_path}"
			removed_skills=$((removed_skills + 1))
		elif [[ -e ${skill_path} ]]; then
			echo "Step 2/3: skipped ${skill_path} (directory not managed by install; leaving in place)"
		fi
	done
	echo "Step 2/3: removed ${removed_skills} managed proactive skill(s)"

	# Step 3/3: Remove global hooks.json LAST, and only if install created it.
	# Select and inspect any restored backup before deleting runtime_dir so custom
	# hooks that still reference ~/.gemini/config/proactive/ keep their target alive.
	local hooks_path="${config_dir}/hooks.json"
	if is_hooks_file_managed "${hooks_path}" "${stamp_file}" "${legacy_root}"; then
		local latest_backup=""
		latest_backup="$(find "${config_dir}" -maxdepth 1 -name "hooks.json.backup.[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]" -type f 2>/dev/null | sort -r | head -n 1 || true)"
		rm -f "${hooks_path}"
		if [[ -n ${latest_backup} ]] && [[ -f ${latest_backup} ]]; then
			mv "${latest_backup}" "${hooks_path}"
			echo "Step 3/3: restored previous hooks.json from ${latest_backup}"
			local sanitize_rc=0
			sanitize_restored_hooks "${hooks_path}" || sanitize_rc=$?
			case "${sanitize_rc}" in
			0)
				rm -rf "${runtime_dir}"
				;;
			10)
				echo "Step 3/3: preserved ${runtime_dir} because restored hooks.json still references .gemini/config/proactive (manual cleanup may be needed)"
				;;
			11)
				echo "Step 3/3: preserved ${runtime_dir} because restored hooks.json could not be parsed as JSON" >&2
				;;
			*)
				echo "Step 3/3: preserved ${runtime_dir} (hooks inspection exited ${sanitize_rc})" >&2
				;;
			esac
		else
			rm -rf "${runtime_dir}"
			echo "Step 3/3: removed global hooks.json (local reports and worktrees preserved)"
		fi
	elif [[ -L ${hooks_path} ]] || [[ -e ${hooks_path} ]]; then
		echo "Step 3/3: skipped ${hooks_path} (not managed by install; leaving in place)"
	else
		rm -rf "${runtime_dir}"
		echo "Step 3/3: hooks.json already removed"
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
	doctor)
		cmd_doctor "$@"
		;;
	stage-repo)
		cmd_stage_repo "$@"
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
	sweep-date)
		cmd_sweep_date "$@"
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
