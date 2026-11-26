#!/usr/bin/env bash
#
# Control and Ordered-Rollback Script for Antigravity Proactive Workflows.
# Manages copy-on-deploy skills, safety hook, and runtime scripts under
# $HOME/.gemini/config/proactive (decoupled from the repo working tree), chmod 700
# report and transcript permissions, staged sidecars with optional weekday
# staggering (without ever self-enabling user_config.json), disposable
# timezone-aware cron canaries, verified post-merge Sentinel leases, MISSED slot
# auditing, base-relative classification of verify failures, and two-tier
# post-sweep Judge evaluation (Tier 1 local/graph gates + Tier 2 CodeRabbit,
# open-code-review, and sparing LiveReview) with a 0600 shadow ledger.

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
  antigravity-proactive-ctl.sh stage-repo --repo <name> [--stagger] [--cron "<expr>"] [--triage-cron "<expr>"] [--repo-path <dir>]
  antigravity-proactive-ctl.sh canary-stage [--offset-minutes <n>] [--timezone <iana_tz>]
  antigravity-proactive-ctl.sh canary-clean
  antigravity-proactive-ctl.sh sentinel-post-merge --repo <name> --pr <number>
  antigravity-proactive-ctl.sh audit-missed --date <YYYY-MM-DD> --repo <name>
  antigravity-proactive-ctl.sh sweep-date --cron "<expr>" [--now "<ISO-8601>"]
  antigravity-proactive-ctl.sh base-check --repo <name> --worktree <dir> [--digest <path>] [--test-cmd <cmd>]
  antigravity-proactive-ctl.sh judge [--repo <name> ...] [--all-repos] [--date <YYYY-MM-DD>] [--cron "<expr>"] [--worktree-root <dir>] [--repo-root-parent <dir>] [--max-age-days <days>] [--now-epoch <sec>] [--skip-tier2] [--with-lrc] [--force-rejudge]
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

	if ! install -m "${mode}" "${src}" "${tmp_dst}"; then
		rm -f "${tmp_dst}"
		return 1
	fi
	if ! python3 -c 'import os, sys; os.replace(sys.argv[1], sys.argv[2])' "${tmp_dst}" "${dst}"; then
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

	mkdir -p "$(dirname "${dst_file}")" "$(dirname "${stamp_file}")"

	local backup_file=""
	if [[ -L ${dst_file} ]]; then
		:
	elif [[ -f ${dst_file} ]] && ! is_hooks_file_managed "${dst_file}" "${stamp_file}" "${legacy_root}"; then
		local backup_ts=""
		backup_ts="$(date -u +%Y%m%d_%H%M%S)"
		backup_file="${dst_file}.backup.${backup_ts}"
		if ! install -m 600 "${dst_file}" "${backup_file}"; then
			rm -f "${backup_file}"
			echo "[ERROR] Failed to back up unmanaged hooks file: ${dst_file}" >&2
			return 1
		fi
	fi

	if ! atomic_install_file 600 "${src_file}" "${dst_file}"; then
		if [[ -n ${backup_file} ]] && [[ -f ${backup_file} ]] && [[ ! -e ${dst_file} ]]; then
			cp -p "${backup_file}" "${dst_file}" 2>/dev/null || true
		fi
		echo "[ERROR] Failed to install hooks file into ${dst_file}" >&2
		return 1
	fi

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
            if isinstance(cmd, str) and ".gemini/config/proactive/hooks/proactive-guard.py" in cmd:
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
	local stagger=0
	local explicit_cron=0
	local explicit_triage_cron=0
	local repo_path=""

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--repo)
			require_flag_value "stage-repo" "$1" "$#"
			repo_name="${2##*/}"
			shift 2
			;;
		--stagger)
			stagger=1
			shift
			;;
		--cron)
			require_flag_value "stage-repo" "$1" "$#"
			sweep_cron="$2"
			explicit_cron=1
			shift 2
			;;
		--triage-cron)
			require_flag_value "stage-repo" "$1" "$#"
			triage_cron="$2"
			explicit_triage_cron=1
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

	if [[ ${stagger} -eq 1 ]]; then
		local stag_sweep=""
		local stag_triage=""
		case "${repo_name}" in
		ctrld-sync)
			stag_sweep="CRON_TZ=America/Chicago 15 8 * * 1-5"
			stag_triage="CRON_TZ=America/Chicago 35 8 * * 1-5"
			;;
		email-security-pipeline)
			stag_sweep="CRON_TZ=America/Chicago 40 8 * * 1-5"
			stag_triage="CRON_TZ=America/Chicago 0 9 * * 1-5"
			;;
		personal-config)
			stag_sweep="CRON_TZ=America/Chicago 5 9 * * 1-5"
			stag_triage="CRON_TZ=America/Chicago 25 9 * * 1-5"
			;;
		Hydrograph_Versus_Seatek_Sensors_Project)
			stag_sweep="CRON_TZ=America/Chicago 30 9 * * 1-5"
			stag_triage="CRON_TZ=America/Chicago 50 9 * * 1-5"
			;;
		Seatek_Analysis)
			stag_sweep="CRON_TZ=America/Chicago 55 9 * * 1-5"
			stag_triage="CRON_TZ=America/Chicago 15 10 * * 1-5"
			;;
		series_correction_project_updated)
			stag_sweep="CRON_TZ=America/Chicago 20 10 * * 1-5"
			stag_triage="CRON_TZ=America/Chicago 40 10 * * 1-5"
			;;
		repoprompt-ce)
			stag_sweep="CRON_TZ=America/Chicago 45 10 * * 1-5"
			stag_triage="CRON_TZ=America/Chicago 5 11 * * 1-5"
			;;
		*)
			stag_sweep="CRON_TZ=America/Chicago 10 11 * * 1-5"
			stag_triage="CRON_TZ=America/Chicago 30 11 * * 1-5"
			;;
		esac
		if [[ ${explicit_cron} -eq 0 ]]; then
			sweep_cron="${stag_sweep}"
		fi
		if [[ ${explicit_triage_cron} -eq 0 ]]; then
			triage_cron="${stag_triage}"
		fi
	fi

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

marker_name = ".managed-by-proactive-ctl"
for existing_path in (sweep_path, triage_path):
    if existing_path.parent.is_symlink() or existing_path.is_symlink():
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
        if not (existing_path.parent / marker_name).is_file():
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
quoted_repo_path = shlex.quote(repo_path)

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
    f"run Step 0 {worktree_sh} preflight --repo abhimehro/{repo_name} --repo-path {quoted_repo_path} --auto-heal, "
    f"then run {worktree_sh} cleanup --ttl-days 21 and check-throttle --repo abhimehro/{repo_name} "
    f"--include-worktrees --repo-path {quoted_repo_path} --auto-expire, "
    f"check open-PR and live-worktree file collisions via check-collisions --repo abhimehro/{repo_name} "
    f"--include-worktrees --repo-path {quoted_repo_path} --file <relpath> "
    "(repeatable for each proposed edit) before editing, "
    f"prepare an isolated local worktree via prepare --repo abhimehro/{repo_name} "
    f"--repo-path {quoted_repo_path} --lens <lens> --mode local, "
    f"{verify_guidance} without modifying build, lock, script, or test harnesses, "
    "and if verify reports a semantic test-coverage BLOCK restore the lost coverage rather than deleting "
    "tests or pinning --expected-test-count, resolve SWEEP_DATE via "
    f"`{ctl_sh} sweep-date --cron {quoted_cron}`, and write a chmod 600 digest report to "
    f"{reports_dir}/$SWEEP_DATE-{repo_name}.md. Do not push branches, open PRs, or edit .jules/sentinel.md."
)

triage_prompt = (
    f"[PROACTIVE-JUDGE-SHADOW] Post-sweep Judge & queue resolution for {repo_name} "
    "(2B, shadow-ledger + two-tier state transitions). "
    "Do NOT push, open PRs, or re-run the sweep. Steps: "
    f"(1) Resolve SWEEP_DATE via `{ctl_sh} sweep-date --cron {quoted_cron}` and check {reports_dir}/$SWEEP_DATE-{repo_name}.md. "
    f"(2) If no digest exists, run `{ctl_sh} audit-missed --date \"$SWEEP_DATE\" --repo {repo_name} --cron {quoted_cron}` once. "
    f"(3) Run `{ctl_sh} judge --repo {repo_name} --date \"$SWEEP_DATE\" --cron {quoted_cron}` to evaluate all UNJUDGED "
    "candidate worktrees across Tier 1 (merge-tree, check-collisions, open-code-review, gitnexus-review) and Tier 2 "
    "(CodeRabbit, plus sparing LiveReview `lrc` only on eligible tie-breakers; never transmit sentinel diffs to cloud reviewers), "
    "run base-check automatically on any non-zero verify failure, retire JUDGE_REJECT regressions, transition "
    "JUDGE_PASS_ROUTINE / JUDGE_ESCALATE_HUMAN worktrees to JUDGED, auto-expire >7d JUDGED worktrees on disk, and append "
    "0600 receipts to judge-shadow-ledger.jsonl. "
    "(4) Post a TIGHT summary with: repo, Status, Substatus, Judge Verdict(s), Queue Health "
    "(unjudged_open, judged_open, expired_preserved), verify exit code, diff size (files/+/-), and a one-line call: "
    "'worth a look' or 'skip'. Never print secrets or sentinel details beyond Status and local digest path."
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
    "display_name": f"Proactive Judge & Triage ({repo_name})",
    "description": (
        f"Scheduled ({triage_cron}) post-sweep Judge & queue resolution for {repo_name}; "
        "evaluates proactive digests and unjudged candidate worktrees."
    ),
    "agent_permissions": {
        "allows_user_interactions": True,
        "workspace_uris": [f"file://{reports_dir}"],
        "access_grants": [
            f"read_file({repo_path})",
            f"read_file({reports_dir})",
            f"write_file({reports_dir})",
            f"read_file({worktrees_dir})",
            f"write_file({worktrees_dir})",
            f"command({home_dir}/bin/agent-zsh -c)",
            f"command({ctl_sh} sweep-date)",
            f"command({ctl_sh} audit-missed)",
            f"command({ctl_sh} base-check)",
            f"command({ctl_sh} judge)",
            f"command({ctl_sh} doctor)",
            f"command({worktree_sh})",
            "command(ocr)",
            "command(coderabbit)",
            "command(lrc)",
            "command(node)",
            "command(git -C)",
        ],
    },
}


def atomic_write_text_0600(dst: pathlib.Path, text: str) -> None:
    tmp = dst.with_name(f".{dst.name}.tmp.{os.getpid()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, dst)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


atomic_write_text_0600(sweep_path, json.dumps(sweep_doc, indent=2) + "\n")
atomic_write_text_0600(triage_path, json.dumps(triage_doc, indent=2) + "\n")
atomic_write_text_0600(sweep_path.parent / marker_name, "managed\n")
atomic_write_text_0600(triage_path.parent / marker_name, "managed\n")
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
    local_day = day
    local = datetime.datetime.combine(day, datetime.time(hour, minute), tzinfo=zone)
    for offset in (-1, 0, 1):
        cand_day = day + datetime.timedelta(days=offset)
        cand_local = datetime.datetime.combine(
            cand_day, datetime.time(hour, minute), tzinfo=zone
        )
        if cand_local.astimezone(datetime.timezone.utc).date() == day:
            local_day = cand_day
            local = cand_local
            break
    utc_hm = local.astimezone(datetime.timezone.utc).strftime("%H:%M")
    if tz_name == "UTC":
        print(f"{local_day.isoformat()} {hour:02d}:{minute:02d} UTC")
    else:
        print(f"{local_day.isoformat()} {hour:02d}:{minute:02d} {tz_name} ({utc_hm} UTC)")
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
				if [[ -d "${dir%/}/src" ]]; then
					seg_pythonpath="${dir%/}/src:${dir%/}${seg_pythonpath:+:${seg_pythonpath}}"
				else
					seg_pythonpath="${dir%/}${seg_pythonpath:+:${seg_pythonpath}}"
				fi
			fi
		fi
		(
			cd "${dir}" || exit 1
			if [[ -n ${seg_pythonpath} ]]; then
				PYTHONDONTWRITEBYTECODE=1 PATH="${seg_path}" PYTHONPATH="${seg_pythonpath}" env -u SSH_AUTH_SOCK -u GH_TOKEN -u GITHUB_TOKEN -u VIRTUAL_ENV bash -c "${seg}"
			else
				PYTHONDONTWRITEBYTECODE=1 PATH="${seg_path}" env -u SSH_AUTH_SOCK -u GH_TOKEN -u GITHUB_TOKEN -u VIRTUAL_ENV bash -c "${seg}"
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
			if run_segment_in "${BASE_CHECK_WT}" "${cand_fail_seg}" "${BASE_CHECK_DIR}/base-${cand_fail_idx}.log" "${repo_path}"; then
				verdict="CAUSED_BY_CHANGE"
				substatus="GATE_FAILURE"
				detail="stage ${cand_fail_idx} (${cand_fail_seg}) passes at base_sha ${base_sha} but fails in the candidate; this is a real regression, discard the candidate"
			else
				verdict="PRE_EXISTING_ON_BASE"
				substatus="PRE_EXISTING_FAILURE"
				detail="base_sha ${base_sha} also fails stage ${cand_fail_idx} (${cand_fail_seg}). Promote the candidate and file the base breakage separately."
				tail -n 15 "${BASE_CHECK_DIR}/base-${cand_fail_idx}.log" >&2 || true
			fi
		fi
	fi

	local bc_head="" bc_fp=""
	bc_head="$(git -C "${wt_path}" rev-parse --verify --quiet HEAD 2>/dev/null || true)"
	bc_fp="$(
		python3 - "${wt_path}" "${bc_head}" <<'PY' 2>/dev/null || true
import hashlib
import os
import subprocess
import sys

wt_dir_str, head_val = sys.argv[1], sys.argv[2]
h = hashlib.sha256()
h.update(f"HEAD:{head_val}\n".encode("utf-8"))
st = subprocess.run(
    ["git", "-C", wt_dir_str, "status", "--porcelain=v1", "-z", "--untracked-files=all"],
    capture_output=True,
)
h.update(st.stdout or b"")
diff = subprocess.run(
    ["git", "-C", wt_dir_str, "diff", "--no-ext-diff", "--binary", "HEAD"],
    capture_output=True,
)
h.update(diff.stdout or b"")
untracked = subprocess.run(
    ["git", "-C", wt_dir_str, "ls-files", "--others", "--exclude-standard", "-z"],
    capture_output=True,
)
for raw_rel in (untracked.stdout or b"").split(b"\x00"):
    if not raw_rel:
        continue
    rel = raw_rel.decode("utf-8", errors="replace")
    p = os.path.join(wt_dir_str, rel)
    h.update(rel.encode("utf-8") + b"\x00")
    try:
        if os.path.islink(p):
            h.update(b"L:" + os.readlink(p).encode("utf-8", errors="replace") + b"\x00")
        elif os.path.isfile(p):
            with open(p, "rb") as fh:
                data = fh.read()
            h.update(f"F:{len(data)}:".encode("utf-8") + data + b"\x00")
    except OSError:
        h.update(b"ERR\x00")
print(h.hexdigest())
PY
	)"

	echo "VERDICT: ${verdict}"
	echo "SUBSTATUS: ${substatus}"
	echo "REPO: abhimehro/${repo_name}"
	echo "BASE_SHA: ${base_sha}"
	echo "WORKTREE: ${wt_path}"
	echo "CONTENT_FINGERPRINT: ${bc_fp}"
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
				echo "- Head SHA: ${bc_head}"
				echo "- Content Fingerprint: ${bc_fp}"
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

cmd_judge() {
	local all_repos=0
	local date_str=""
	local cron_expr="CRON_TZ=America/Chicago 15 8 * * 1-5"
	local wt_root="${HOME}/.gemini/antigravity/worktrees"
	local repo_root_parent="${HOME}/dev"
	local max_age_days="7"
	local now_epoch=""
	local skip_tier2=0
	local with_lrc=0
	local force_rejudge=0
	local -a explicit_repos=()

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--repo)
			require_flag_value "judge" "$1" "$#"
			local r_arg=""
			r_arg="${2##*/}"
			validate_repo_name "${r_arg}" "judge"
			explicit_repos+=("${r_arg}")
			shift 2
			;;
		--all-repos)
			all_repos=1
			shift
			;;
		--date)
			require_flag_value "judge" "$1" "$#"
			date_str="$2"
			shift 2
			;;
		--cron)
			require_flag_value "judge" "$1" "$#"
			cron_expr="$2"
			shift 2
			;;
		--worktree-root)
			require_flag_value "judge" "$1" "$#"
			wt_root="$2"
			shift 2
			;;
		--repo-root-parent)
			require_flag_value "judge" "$1" "$#"
			repo_root_parent="$2"
			shift 2
			;;
		--max-age-days)
			require_flag_value "judge" "$1" "$#"
			max_age_days="$2"
			shift 2
			;;
		--now-epoch)
			require_flag_value "judge" "$1" "$#"
			now_epoch="$2"
			shift 2
			;;
		--skip-tier2)
			skip_tier2=1
			shift
			;;
		--with-lrc)
			with_lrc=1
			shift
			;;
		--force-rejudge)
			force_rejudge=1
			shift
			;;
		*)
			echo "[ERROR] Unknown flag for judge: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ ! ${max_age_days} =~ ^[0-9]+$ ]]; then
		echo "[ERROR] judge: --max-age-days must be a non-negative integer, got: ${max_age_days}" >&2
		exit 1
	fi
	if [[ -n ${now_epoch} ]] && [[ ! ${now_epoch} =~ ^[0-9]+$ ]]; then
		echo "[ERROR] judge: --now-epoch must be a non-negative integer, got: ${now_epoch}" >&2
		exit 1
	fi

	local sweep_date=""
	if [[ -n ${date_str} ]]; then
		if [[ ! ${date_str} =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
			echo "[ERROR] judge: --date must be YYYY-MM-DD, got: ${date_str}" >&2
			exit 1
		fi
		if ! python3 -c 'import datetime, sys; datetime.date.fromisoformat(sys.argv[1])' "${date_str}" >/dev/null 2>&1; then
			echo "[ERROR] judge: invalid calendar --date: ${date_str}" >&2
			exit 1
		fi
		sweep_date="${date_str}"
	else
		sweep_date="$(cmd_sweep_date --cron "${cron_expr}")"
	fi

	local worktree_sh=""
	if [[ -x "${SCRIPT_DIR}/proactive-worktree.sh" ]]; then
		worktree_sh="${SCRIPT_DIR}/proactive-worktree.sh"
	elif [[ -x "${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh" ]]; then
		worktree_sh="${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh"
	else
		echo "[ERROR] judge: proactive-worktree.sh not found or not executable" >&2
		exit 1
	fi

	local ctl_sh="${SCRIPT_DIR}/antigravity-proactive-ctl.sh"
	local reports_dir="${HOME}/.gemini/antigravity/proactive-reports"
	mkdir -p "${reports_dir}"
	chmod 700 "${reports_dir}"

	local ledger_file="${reports_dir}/judge-shadow-ledger.jsonl"
	if [[ -L ${ledger_file} ]]; then
		echo "[ERROR] judge: refusing symlinked ledger path: ${ledger_file}" >&2
		exit 1
	fi
	(
		umask 077
		: >>"${ledger_file}"
		chmod 600 "${ledger_file}"
	)

	local -a target_repos=()
	if [[ ${#explicit_repos[@]} -gt 0 ]]; then
		target_repos=("${explicit_repos[@]}")
	elif [[ ${all_repos} -eq 1 ]]; then
		target_repos=("${ALL_PROACTIVE_REPOS[@]}")
	else
		target_repos=("ctrld-sync")
	fi

	python3 - "${worktree_sh}" "${ctl_sh}" "${reports_dir}" "${ledger_file}" "${sweep_date}" "${wt_root}" "${repo_root_parent}" "${max_age_days}" "${now_epoch}" "${skip_tier2}" "${with_lrc}" "${force_rejudge}" "${target_repos[@]}" <<'PY'
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile

worktree_sh = sys.argv[1]
ctl_sh = sys.argv[2]
reports_dir = pathlib.Path(sys.argv[3])
ledger_path = pathlib.Path(sys.argv[4])
sweep_date = sys.argv[5]
wt_root = pathlib.Path(sys.argv[6])
repo_root_parent = pathlib.Path(sys.argv[7])
max_age_days = int(sys.argv[8])
now_epoch = int(sys.argv[9]) if sys.argv[9] else int(dt.datetime.now(dt.timezone.utc).timestamp())
skip_tier2 = sys.argv[10] == "1"
with_lrc = sys.argv[11] == "1"
force_rejudge = sys.argv[12] == "1"
target_repos = sys.argv[13:]

RESEARCH_REPOS = {
    "Hydrograph_Versus_Seatek_Sensors_Project",
    "Seatek_Analysis",
    "series_correction_project_updated",
}
RISK_ORDER = {"NONE": 0, "UNKNOWN": 1, "LOW": 2, "MEDIUM": 3, "HIGH": 4, "CRITICAL": 5}
EXPIRE_DATE = (dt.date.fromisoformat(sweep_date) + dt.timedelta(days=max_age_days)).isoformat()


def run_bounded(cmd, cwd=None, timeout_s=60):
    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            start_new_session=True,
        )
        out, err = proc.communicate(timeout=timeout_s)
        return proc.returncode, out, err
    except subprocess.TimeoutExpired:
        if proc is not None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
            if proc.poll() is None:
                proc.wait()
        return 124, "", f"timed out after {timeout_s}s: {cmd[0]}"
    except FileNotFoundError:
        return 127, "", f"command not found: {cmd[0]}"


def load_ledger_rows():
    rows = []
    if not ledger_path.is_file():
        return rows
    for raw_line in ledger_path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            obj = json.loads(raw_line)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows


LEDGER_ROWS = load_ledger_rows()


def append_ledger_row(row):
    if ledger_path.is_symlink():
        raise RuntimeError(f"Refusing symlinked ledger path: {ledger_path}")
    payload = json.dumps(row, sort_keys=False) + "\n"
    fd = os.open(ledger_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.chmod(ledger_path, 0o600)
    except Exception:
        raise
    LEDGER_ROWS.append(row)


def has_idempotent_row(date_val, repo_val, digest_status, worktree_key):
    for row in LEDGER_ROWS:
        if (
            row.get("date") == date_val
            and row.get("repo") == repo_val
            and row.get("digest_status") == digest_status
            and row.get("worktree_key", row.get("worktree", "")) == worktree_key
        ):
            return True
    return False


def count_daily_lrc_runs(date_val):
    return sum(
        1
        for row in LEDGER_ROWS
        if row.get("date") == date_val and row.get("lrc_executed") is True
    )


def parse_digest_field(text, field_name):
    pat = rf"(?im)^\s*(?:-\s*)?(?:\*\*)?{re.escape(field_name)}(?:\*\*)?\s*:\s*(?:\*\*)?\s*`?([A-Za-z0-9_-]+)`?"
    match = re.search(pat, text)
    return match.group(1).strip() if match else ""


def append_judge_section_to_digest(digest_file, section_text, head_sha):
    if digest_file is None or not digest_file.exists() or digest_file.is_symlink():
        return
    existing = digest_file.read_text(encoding="utf-8", errors="replace")
    marker = "\n## Judge Evaluation\n"
    if marker in existing or existing.startswith("## Judge Evaluation\n"):
        if force_rejudge:
            if existing.startswith("## Judge Evaluation\n"):
                existing = ""
            else:
                existing = existing.split(marker, 1)[0].rstrip() + "\n"
        elif head_sha and f"- Head SHA: {head_sha}" in existing:
            os.chmod(digest_file, 0o600)
            return
    updated = existing.rstrip() + "\n\n" + section_text.strip() + "\n"
    tmp = digest_file.with_name(f".{digest_file.name}.tmp.{os.getpid()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(updated)
        os.chmod(tmp, 0o600)
        os.replace(tmp, digest_file)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def is_git_repo(path_obj):
    if path_obj is None or not path_obj.is_dir():
        return False
    rc, _, _ = run_bounded(["git", "-C", str(path_obj), "rev-parse", "--git-dir"], timeout_s=10)
    return rc == 0


def read_wt_meta(wt_dir):
    rc, out, _ = run_bounded(["git", "-C", str(wt_dir), "rev-parse", "--git-dir"], timeout_s=10)
    if rc != 0 or not out.strip():
        return None, {}
    raw_git = out.strip()
    git_dir = pathlib.Path(raw_git) if os.path.isabs(raw_git) else (wt_dir / raw_git).resolve()
    meta_file = git_dir / "proactive-meta.json"
    if not meta_file.is_file():
        return git_dir, {}
    try:
        return git_dir, json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return git_dir, {}


def abs_git_key(wt_dir):
    rc, out, _ = run_bounded(["git", "-C", str(wt_dir), "rev-parse", "--absolute-git-dir"], timeout_s=10)
    if rc != 0 or not out.strip():
        return ""
    return os.path.realpath(out.strip())


def discover_repo_worktrees(repo, default_repo_dir):
    seen = set()
    discovered = []
    meta_repo_paths = []
    default_wt_seen = False
    default_real = os.path.realpath(str(default_repo_dir)) if is_git_repo(default_repo_dir) else ""

    def record_repo_path(rp_str):
        if rp_str and pathlib.Path(rp_str).is_dir() and is_git_repo(pathlib.Path(rp_str)):
            rp_real = os.path.realpath(rp_str)
            if all(os.path.realpath(x) != rp_real for x in meta_repo_paths):
                meta_repo_paths.append(rp_str)

    def add_wt(cand_path, require_meta_match=False, from_default_scan=False):
        nonlocal default_wt_seen
        if not cand_path.is_dir():
            return
        key = abs_git_key(cand_path)
        if not key or key in seen:
            return
        _, meta = read_wt_meta(cand_path)
        rc_b, br_out, _ = run_bounded(
            ["git", "-C", str(cand_path), "symbolic-ref", "--quiet", "--short", "HEAD"],
            timeout_s=10,
        )
        branch = br_out.strip() if rc_b == 0 else ""
        meta_repo = meta.get("repo_name", "")
        if meta_repo and meta_repo != repo:
            return
        if require_meta_match and not meta_repo and not branch.startswith("proactive/"):
            return
        if not meta_repo and not branch.startswith("proactive/"):
            return
        seen.add(key)
        discovered.append(cand_path)
        rp = meta.get("repo_path", "")
        if rp:
            record_repo_path(rp)
        elif from_default_scan:
            default_wt_seen = True

    if wt_root.is_dir():
        prefix = f"proactive-{repo}-"
        for entry in sorted(wt_root.iterdir()):
            if entry.name.startswith(prefix) and entry.is_dir():
                add_wt(entry, require_meta_match=False)

    scan_repos = []
    if is_git_repo(default_repo_dir):
        scan_repos.append(default_repo_dir)
    for rp_str in meta_repo_paths:
        rp_obj = pathlib.Path(rp_str)
        if is_git_repo(rp_obj) and all(os.path.realpath(str(x)) != os.path.realpath(str(rp_obj)) for x in scan_repos):
            scan_repos.append(rp_obj)

    for repo_dir in scan_repos:
        is_def = bool(default_real and os.path.realpath(str(repo_dir)) == default_real)
        rc_t, top_out, _ = run_bounded(["git", "-C", str(repo_dir), "rev-parse", "--show-toplevel"], timeout_s=10)
        main_top = os.path.realpath(top_out.strip()) if rc_t == 0 and top_out.strip() else ""
        rc_l, list_out, _ = run_bounded(["git", "-C", str(repo_dir), "worktree", "list", "--porcelain"], timeout_s=15)
        if rc_l != 0:
            continue
        for line in list_out.splitlines():
            if not line.startswith("worktree "):
                continue
            wt_str = line[len("worktree "):].strip()
            if not wt_str:
                continue
            if main_top and os.path.realpath(wt_str) == main_top:
                continue
            add_wt(pathlib.Path(wt_str), require_meta_match=True, from_default_scan=is_def)

    owning_repos = [pathlib.Path(rp) for rp in meta_repo_paths]
    if is_git_repo(default_repo_dir) and (default_wt_seen or not owning_repos):
        if all(os.path.realpath(str(x)) != default_real for x in owning_repos):
            owning_repos.append(default_repo_dir)
    effective_repo = owning_repos[0] if owning_repos else None
    return discovered, effective_repo, owning_repos


def is_gh_usable_for_repo(repo_dir):
    gh_bin = shutil.which("gh")
    if not gh_bin:
        return False
    rc_u, url_out, _ = run_bounded(["git", "-C", str(repo_dir), "remote", "get-url", "origin"], timeout_s=10)
    origin_url = url_out.strip() if rc_u == 0 else ""
    is_local_origin = bool(origin_url) and os.path.exists(origin_url)
    if not is_local_origin:
        return True
    # Local bare-repo origin (offline unit tests): use gh when mocked or authenticated,
    # and avoid false auth failures from system gh under an isolated temp HOME.
    rc_a, _, _ = run_bounded([gh_bin, "auth", "status", "--hostname", "github.com"], timeout_s=10)
    return rc_a == 0


def is_local_origin_repo(repo_dir):
    if repo_dir is None:
        return False
    rc_u, url_out, _ = run_bounded(["git", "-C", str(repo_dir), "remote", "get-url", "origin"], timeout_s=10)
    origin_url = url_out.strip() if rc_u == 0 else ""
    return bool(origin_url) and os.path.exists(origin_url)


def check_local_worktree_collisions(repo_dir, exclude_wt, changed_files):
    if repo_dir is None or not is_git_repo(repo_dir) or not changed_files:
        return 0
    ex_key = abs_git_key(exclude_wt)
    rc_t, top_out, _ = run_bounded(["git", "-C", str(repo_dir), "rev-parse", "--show-toplevel"], timeout_s=10)
    main_top = os.path.realpath(top_out.strip()) if rc_t == 0 and top_out.strip() else ""
    rc_l, list_out, _ = run_bounded(["git", "-C", str(repo_dir), "worktree", "list", "--porcelain"], timeout_s=15)
    if rc_l != 0:
        return 6
    target_set = {os.path.normpath(p) for p in changed_files if p}
    for line in list_out.splitlines():
        if not line.startswith("worktree "):
            continue
        cand_str = line[len("worktree "):].strip()
        if not cand_str:
            continue
        if main_top and os.path.realpath(cand_str) == main_top:
            continue
        cand_path = pathlib.Path(cand_str)
        if not cand_path.is_dir():
            continue
        if ex_key and abs_git_key(cand_path) == ex_key:
            continue
        _, meta = read_wt_meta(cand_path)
        rc_b, br_out, _ = run_bounded(["git", "-C", str(cand_path), "symbolic-ref", "--quiet", "--short", "HEAD"], timeout_s=10)
        br = br_out.strip() if rc_b == 0 else ""
        if not meta and not br.startswith("proactive/"):
            continue
        if not is_active_candidate_wt(cand_path, meta):
            continue
        c_base = meta.get("base_sha", "")
        if not c_base:
            return 6
        rc_df, d_out, _ = run_bounded(["git", "-C", str(cand_path), "diff", "--no-renames", "--name-only", c_base], timeout_s=15)
        rc_ls, u_out, _ = run_bounded(["git", "-C", str(cand_path), "ls-files", "--others", "--exclude-standard"], timeout_s=15)
        if rc_df != 0 or rc_ls != 0:
            return 6
        touched = {os.path.normpath(x.strip()) for x in (d_out + "\n" + u_out).splitlines() if x.strip()}
        if touched & target_set:
            return 4
    return 0


def is_active_candidate_wt(wt_dir, meta):
    rc_d, dirty_out, _ = run_bounded(["git", "-C", str(wt_dir), "status", "--porcelain"], timeout_s=10)
    if rc_d != 0 or dirty_out.strip():
        return True
    base_sha = meta.get("base_sha", "")
    default_branch = meta.get("default_branch", "main") or "main"
    if not base_sha:
        return False
    rc_v, _, _ = run_bounded(["git", "-C", str(wt_dir), "rev-parse", "--verify", "--quiet", f"{base_sha}^{{commit}}"], timeout_s=10)
    if rc_v != 0:
        return True
    rc_a, ahead_out, _ = run_bounded(["git", "-C", str(wt_dir), "rev-list", "--count", f"{base_sha}..HEAD"], timeout_s=10)
    if rc_a != 0 or not ahead_out.strip():
        return True
    if int(ahead_out.strip()) <= 0:
        return False
    rc_o, _, _ = run_bounded(["git", "-C", str(wt_dir), "rev-parse", "--verify", "--quiet", f"origin/{default_branch}"], timeout_s=10)
    if rc_o == 0:
        rc_m, _, _ = run_bounded(["git", "-C", str(wt_dir), "merge-base", "--is-ancestor", "HEAD", f"origin/{default_branch}"], timeout_s=10)
        if rc_m == 0:
            return False
    return True


def compute_wt_content_fingerprint(wt_dir, head_sha_val):
    h = hashlib.sha256()
    h.update(f"HEAD:{head_sha_val}\n".encode("utf-8"))
    st = subprocess.run(
        ["git", "-C", str(wt_dir), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        capture_output=True,
    )
    h.update(st.stdout or b"")
    diff = subprocess.run(
        ["git", "-C", str(wt_dir), "diff", "--no-ext-diff", "--binary", "HEAD"],
        capture_output=True,
    )
    h.update(diff.stdout or b"")
    untracked = subprocess.run(
        ["git", "-C", str(wt_dir), "ls-files", "--others", "--exclude-standard", "-z"],
        capture_output=True,
    )
    for raw_rel in (untracked.stdout or b"").split(b"\x00"):
        if not raw_rel:
            continue
        rel = raw_rel.decode("utf-8", errors="replace")
        p = os.path.join(str(wt_dir), rel)
        h.update(rel.encode("utf-8") + b"\x00")
        try:
            if os.path.islink(p):
                h.update(b"L:" + os.readlink(p).encode("utf-8", errors="replace") + b"\x00")
            elif os.path.isfile(p):
                with open(p, "rb") as fh:
                    data = fh.read()
                h.update(f"F:{len(data)}:".encode("utf-8") + data + b"\x00")
        except OSError:
            h.update(b"ERR\x00")
    return h.hexdigest()


def effective_wt_bucket(wt_dir, meta):
    rc_d, dirty_out, _ = run_bounded(["git", "-C", str(wt_dir), "status", "--porcelain"], timeout_s=10)
    dirty = (rc_d != 0) or bool(dirty_out.strip())
    rc_h, head_out, _ = run_bounded(["git", "-C", str(wt_dir), "rev-parse", "--verify", "--quiet", "HEAD"], timeout_s=10)
    head_sha = head_out.strip() if rc_h == 0 else ""
    raw_state = meta.get("lifecycle_state", "UNJUDGED")
    judged_sha = meta.get("judged_head_sha", "")
    expired_sha = meta.get("expired_head_sha") or judged_sha
    live_fp = compute_wt_content_fingerprint(wt_dir, head_sha) if (dirty and head_sha) else ""

    if dirty:
        if (
            raw_state == "EXPIRED"
            and head_sha
            and expired_sha == head_sha
            and meta.get("expired_dirty_fingerprint")
            and meta.get("expired_dirty_fingerprint") == live_fp
        ):
            bucket = "EXPIRED"
        elif (
            raw_state == "JUDGED"
            and head_sha
            and judged_sha == head_sha
            and meta.get("judged_dirty_fingerprint")
            and meta.get("judged_dirty_fingerprint") == live_fp
        ):
            bucket = "JUDGED"
        else:
            bucket = "UNJUDGED"
    elif raw_state == "EXPIRED" and head_sha and expired_sha == head_sha:
        bucket = "EXPIRED"
    elif raw_state == "JUDGED" and head_sha and judged_sha == head_sha:
        bucket = "JUDGED"
    else:
        bucket = "UNJUDGED"

    age_anchor = meta.get("reopened_at") or meta.get("created_at", "")
    age_days = 0.0
    if age_anchor:
        try:
            anchor_dt = dt.datetime.strptime(age_anchor, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
            age_days = (now_epoch - int(anchor_dt.timestamp())) / 86400.0
        except ValueError:
            age_days = 0.0
    return bucket, dirty, head_sha, age_days


def match_candidate_digest(repo, wt_dir, wt_branch, base_sha, head_sha, today_digest):
    suffix = f"-{repo}.md"
    candidates = [
        p for p in reports_dir.iterdir()
        if p.is_file() and not p.is_symlink() and p.name.endswith(suffix)
    ]
    candidates.sort(key=lambda p: p.name, reverse=True)
    if today_digest in candidates:
        candidates.remove(today_digest)
        candidates.insert(0, today_digest)

    wt_str = str(wt_dir)
    wt_real = os.path.realpath(wt_str)
    short_sha = head_sha[:7] if len(head_sha) >= 7 and head_sha != base_sha else ""
    other_cand_re = re.compile(
        r"(?im)(?:proactive/[A-Za-z0-9._-]+|proactive-[A-Za-z0-9._-]+|^\s*(?:-\s*)?(?:\*\*)?(?:Isolated\s+)?Worktree(?:\s*&\s*Branch)?(?:\*\*)?\s*:\s*`?/[^\s`]+)"
    )

    eligible = []
    for p in candidates:
        txt = p.read_text(encoding="utf-8", errors="replace")
        st_p = parse_digest_field(txt, "Status").upper()
        sub_p = parse_digest_field(txt, "Substatus").upper()
        if st_p in ("THROTTLED", "MISSED", "CLEAN_NO_OP") and sub_p != "GATE_FAILURE":
            continue
        eligible.append((p, txt, st_p))

    exact_matches = [
        (p, txt, st_p)
        for p, txt, st_p in eligible
        if (wt_str in txt or wt_real in txt or (wt_branch and wt_branch in txt))
    ]
    for p, txt, st_p in exact_matches:
        if st_p == "SECURITY_REPORT_ONLY":
            return p, txt
    if exact_matches:
        return exact_matches[0][0], exact_matches[0][1]

    if short_sha:
        sha_matches = [
            (p, txt, st_p)
            for p, txt, st_p in eligible
            if short_sha in txt and not other_cand_re.search(txt)
        ]
        for p, txt, st_p in sha_matches:
            if st_p == "SECURITY_REPORT_ONLY":
                return p, txt
        if sha_matches:
            return sha_matches[0][0], sha_matches[0][1]

    if today_digest.is_file() and not today_digest.is_symlink():
        txt = today_digest.read_text(encoding="utf-8", errors="replace")
        st = parse_digest_field(txt, "Status").upper()
        sub = parse_digest_field(txt, "Substatus").upper()
        names_other_candidate = bool(other_cand_re.search(txt))
        if (st in ("CANDIDATE_READY", "SECURITY_REPORT_ONLY") or sub == "GATE_FAILURE") and not names_other_candidate:
            return today_digest, txt
    return None, ""


def extract_changed_symbols(wt_dir, base_sha, head_ref="HEAD"):
    rc, diff_out, _ = run_bounded(["git", "-C", str(wt_dir), "diff", "-U0", f"{base_sha}..{head_ref}"], timeout_s=20)
    if rc != 0 or not diff_out:
        return []
    syms = []
    patterns = (
        re.compile(r"^[+-]\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
        re.compile(r"^[+-]\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
        re.compile(r"^@@.*?\b(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
        re.compile(r"^[+-]\s*([A-Za-z.][A-Za-z0-9._]*)\s*<-\s*function\b"),
    )
    for line in diff_out.splitlines():
        if line.startswith(("+++", "---")):
            continue
        for pat in patterns:
            m = pat.search(line)
            if m:
                sym = m.group(1)
                if sym not in syms:
                    syms.append(sym)
                if len(syms) >= 5:
                    return syms
    return syms


def count_symbol_test_references(wt_dir, symbols):
    if not symbols:
        return 0
    compiled = [re.compile(rf"\b{re.escape(sym)}\b") for sym in symbols]
    test_files = []
    for root, dirs, files in os.walk(wt_dir):
        dirs[:] = [d for d in dirs if d not in (".git", ".venv", "node_modules", "__pycache__", ".trunk")]
        rel_root = os.path.relpath(root, wt_dir)
        in_tests_dir = any(part in ("tests", "Tests", "test") for part in pathlib.Path(rel_root).parts)
        for fname in files:
            is_test_file = (
                in_tests_dir
                or (fname.startswith("test_") and fname.endswith(".py"))
                or fname.endswith("_test.py")
                or (fname.startswith("test-") and fname.endswith(".R"))
            )
            if is_test_file and fname.endswith((".py", ".R", ".sh")):
                test_files.append(pathlib.Path(root) / fname)

    refs = 0
    for tf in test_files:
        try:
            content = tf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pat in compiled:
            refs += len(pat.findall(content))
    return refs


def parse_ocr_review(raw_text):
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    if not raw_text.strip():
        return False, counts
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return False, counts

    items = None
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for list_key in ("comments", "findings", "issues", "results"):
            if isinstance(data.get(list_key), list):
                items = data[list_key]
                break
        if items is None:
            src = data.get("summary") if isinstance(data.get("summary"), dict) else data
            found_count_key = False
            for sev in ("critical", "high", "medium", "low"):
                if sev in src:
                    val = src.get(sev)
                    if type(val) is int and val >= 0:
                        counts[sev] = val
                        found_count_key = True
                    else:
                        return False, counts
            return found_count_key, counts
    else:
        return False, counts

    for item in items:
        if not isinstance(item, dict):
            continue
        sev = str(item.get("severity") or item.get("level") or "low").strip().lower()
        if sev in counts:
            counts[sev] += 1
        elif sev == "major":
            counts["high"] += 1
    return True, counts


def parse_coderabbit_ndjson(raw_text, rc):
    counts = {"critical": 0, "major": 0, "minor": 0, "trivial": 0, "info": 0, "none": 0}
    status = "unknown"
    parsed_any = False

    def record_finding(fobj):
        sev = str(fobj.get("severity") or fobj.get("level") or "info").strip().lower()
        if sev in counts:
            counts[sev] += 1
        else:
            counts["major"] += 1

    for line in raw_text.splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            ev = json.loads(s)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        parsed_any = True
        ev_type = str(ev.get("type") or "").strip().lower()
        if ev_type == "finding":
            record_finding(ev)
        elif ev_type == "complete":
            status = str(ev.get("status") or "review_completed").strip()
            if isinstance(ev.get("findings"), list):
                for item in ev["findings"]:
                    if isinstance(item, dict):
                        record_finding(item)
        elif ev_type == "action_required" and status == "unknown":
            status = str(ev.get("status") or "action_required").strip()

    if not parsed_any and raw_text.strip():
        try:
            whole = json.loads(raw_text)
            if isinstance(whole, dict):
                status = str(whole.get("status") or status).strip()
                for item in whole.get("findings", []):
                    if isinstance(item, dict):
                        record_finding(item)
        except json.JSONDecodeError:
            pass

    if rc != 0 and status == "review_completed":
        status = f"degraded_exit_{rc}"
    return status, counts


def parse_lrc_usage(raw_text):
    can_trigger = False
    rem_loc = None
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict):
            can_trigger = data.get("can_trigger_reviews") is True
            env = data.get("envelope") if isinstance(data.get("envelope"), dict) else {}
            for candidate in (
                env.get("loc_remaining_month"),
                data.get("loc_remaining_month"),
                data.get("remaining_loc"),
                data.get("loc_remaining"),
            ):
                if isinstance(candidate, (int, float)):
                    rem_loc = int(candidate)
                    break
            if rem_loc is None:
                lim = env.get("loc_limit_month", data.get("loc_limit_month"))
                used = env.get("loc_used_month", data.get("loc_used_month"))
                if isinstance(lim, (int, float)) and isinstance(used, (int, float)):
                    rem_loc = int(lim - used)
            return can_trigger, rem_loc
    except json.JSONDecodeError:
        pass

    if re.search(r"(?i)can_trigger_reviews\s*[:=]\s*true\b", raw_text):
        can_trigger = True
    m_loc = re.search(r"(?i)(?:loc_remaining(?:_month)?|remaining_loc)\s*[:=]\s*([0-9]+)", raw_text)
    if m_loc:
        rem_loc = int(m_loc.group(1))
    return can_trigger, rem_loc


def parse_lrc_review(raw_text, rc):
    counts = {"critical": 0, "high": 0, "major": 0, "medium": 0, "minor": 0, "low": 0}
    if rc != 0:
        return "degraded", counts
    if not raw_text.strip():
        return "completed", counts
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return "degraded", counts

    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for k in ("findings", "comments", "issues", "results"):
            if isinstance(data.get(k), list):
                items = data[k]
                break
    for item in items:
        if not isinstance(item, dict):
            continue
        sev = str(item.get("severity") or item.get("level") or "low").strip().lower()
        if sev in counts:
            counts[sev] += 1
        elif sev not in ("info", "trivial", "none", "nit"):
            counts["major"] += 1
    return "completed", counts


for repo in target_repos:
    default_repo_dir = repo_root_parent / repo
    today_digest = reports_dir / f"{sweep_date}-{repo}.md"
    today_text = ""
    today_status = "MISSING"
    if today_digest.is_file() and not today_digest.is_symlink():
        today_text = today_digest.read_text(encoding="utf-8", errors="replace")
        today_status = parse_digest_field(today_text, "Status").upper() or "UNKNOWN"

    now_iso = dt.datetime.fromtimestamp(now_epoch, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if today_status in ("CLEAN_NO_OP", "MISSED", "THROTTLED"):
        if not has_idempotent_row(sweep_date, repo, today_status, ""):
            append_ledger_row(
                {
                    "timestamp": now_iso,
                    "date": sweep_date,
                    "repo": repo,
                    "digest_status": today_status,
                    "digest_path": str(today_digest),
                    "worktree": "",
                    "worktree_key": "",
                    "branch": "",
                    "base_sha": "",
                    "head_sha": "",
                    "lens": parse_digest_field(today_text, "Lens").lower(),
                    "verdict": "JUDGE_NO_CANDIDATE",
                    "subreason": today_status,
                    "ocr_review": "skipped",
                    "coderabbit": "skipped",
                    "lrc": "skipped_policy",
                    "tier1": {},
                    "tier2": {
                        "ocr_review": "skipped",
                        "coderabbit": "skipped",
                        "lrc": "skipped_policy",
                    },
                    "lrc_executed": False,
                }
            )

    worktrees, effective_repo_dir, owning_repos = discover_repo_worktrees(repo, default_repo_dir)

    # Refresh origin & auto-heal merged worktrees across owning clones (stay offline under --skip-tier2).
    if worktrees and owning_repos:
        if skip_tier2:
            for owner_dir in owning_repos:
                run_bounded(["git", "-C", str(owner_dir), "worktree", "prune"], timeout_s=15)
            run_bounded([worktree_sh, "cleanup", "--worktree-root", str(wt_root), "--prune-merged"], timeout_s=30)
            worktrees, effective_repo_dir, owning_repos = discover_repo_worktrees(repo, default_repo_dir)
        else:
            refreshed_any = False
            for owner_dir in owning_repos:
                rc_orig, orig_out, _ = run_bounded(
                    ["git", "-C", str(owner_dir), "remote", "get-url", "origin"],
                    timeout_s=10,
                )
                origin_url = orig_out.strip() if rc_orig == 0 else ""
                if not origin_url:
                    continue
                refreshed_any = True
                if is_gh_usable_for_repo(owner_dir):
                    pf_rc, pf_out, pf_err = run_bounded(
                        [
                            worktree_sh,
                            "preflight",
                            "--repo",
                            f"abhimehro/{repo}",
                            "--repo-path",
                            str(owner_dir),
                            "--worktree-root",
                            str(wt_root),
                            "--auto-heal",
                        ],
                        timeout_s=90,
                    )
                    if pf_rc != 0:
                        sys.stderr.write(pf_err or pf_out or f"[ERROR] judge: preflight failed (exit {pf_rc}) for {repo}\n")
                        sys.exit(6)
                else:
                    # Offline local-bare-origin test fallback: still enforce fresh local fetch & prune merged.
                    f_rc, _, f_err = run_bounded(
                        ["git", "-C", str(owner_dir), "fetch", "--prune", "--quiet", "origin"],
                        timeout_s=30,
                    )
                    if f_rc != 0:
                        sys.stderr.write(f"[ERROR] judge: git fetch failed for {owner_dir}: {f_err}\n")
                        sys.exit(6)
                    run_bounded(["git", "-C", str(owner_dir), "worktree", "prune"], timeout_s=15)
                    run_bounded([worktree_sh, "cleanup", "--worktree-root", str(wt_root), "--prune-merged"], timeout_s=30)
            if refreshed_any:
                worktrees, effective_repo_dir, owning_repos = discover_repo_worktrees(repo, default_repo_dir)

    active_wts = []
    for wt_dir in worktrees:
        if not wt_dir.is_dir():
            continue
        _, meta = read_wt_meta(wt_dir)
        if is_active_candidate_wt(wt_dir, meta):
            active_wts.append((wt_dir, meta))

    if today_status == "SECURITY_REPORT_ONLY" and not active_wts:
        if not has_idempotent_row(sweep_date, repo, "SECURITY_REPORT_ONLY", "NO_WORKTREE"):
            append_ledger_row(
                {
                    "timestamp": now_iso,
                    "date": sweep_date,
                    "repo": repo,
                    "digest_status": "SECURITY_REPORT_ONLY",
                    "digest_path": str(today_digest),
                    "worktree": "",
                    "worktree_key": "NO_WORKTREE",
                    "branch": "",
                    "base_sha": "",
                    "head_sha": "",
                    "lens": "sentinel",
                    "verdict": "JUDGE_ESCALATE_HUMAN",
                    "subreason": "SECURITY_REPORT_ONLY_LOCAL_BOUNDARY",
                    "ocr_review": "skipped_privacy",
                    "coderabbit": "skipped_privacy",
                    "lrc": "skipped_privacy",
                    "tier1": {"privacy_boundary": "local_only"},
                    "tier2": {
                        "ocr_review": "skipped_privacy",
                        "coderabbit": "skipped_privacy",
                        "lrc": "skipped_privacy",
                    },
                    "lrc_executed": False,
                }
            )
        sec_section = (
            "## Judge Evaluation\n\n"
            f"- Date: {sweep_date}\n"
            "- Head SHA: NO_WORKTREE\n"
            "- Verdict: JUDGE_ESCALATE_HUMAN\n"
            "- Subreason: SECURITY_REPORT_ONLY_LOCAL_BOUNDARY\n"
            "- Tier 1: local_report_only=true\n"
            "- Tier 2: ocr_review=skipped_privacy, coderabbit=skipped_privacy, lrc=skipped_privacy\n"
            f"- Action: promote | reject | expire (default: expire on {EXPIRE_DATE})"
        )
        append_judge_section_to_digest(today_digest, sec_section, "NO_WORKTREE")

    judged_now = 0
    rejected_now = 0
    judge_degraded = False
    gitnexus_refreshed = False

    for wt_dir, meta in active_wts:
        bucket, dirty, head_sha, age_days = effective_wt_bucket(wt_dir, meta)
        eval_fingerprint = compute_wt_content_fingerprint(wt_dir, head_sha) if head_sha else ""
        rc_b, br_out, _ = run_bounded(["git", "-C", str(wt_dir), "symbolic-ref", "--quiet", "--short", "HEAD"], timeout_s=10)
        wt_branch = br_out.strip() if rc_b == 0 else ""
        base_sha = meta.get("base_sha", "")
        default_branch = meta.get("default_branch", "main") or "main"
        lens = (meta.get("lens") or "code-health").strip().lower()
        wt_repo_str = meta.get("repo_path") or (str(effective_repo_dir) if effective_repo_dir else "")
        wt_repo_dir = pathlib.Path(wt_repo_str) if wt_repo_str else None

        # (c) Auto-expire >max_age_days JUDGED worktrees on disk when not --force-rejudge.
        if bucket == "JUDGED" and not force_rejudge:
            if age_days > max_age_days:
                exp_cmd = [
                    worktree_sh,
                    "set-state",
                    "--worktree",
                    str(wt_dir),
                    "--state",
                    "EXPIRED",
                    "--subreason",
                    "SLA_7D_AUTO_EXPIRE",
                ]
                if head_sha:
                    exp_cmd.extend(["--expected-head", head_sha])
                if dirty:
                    exp_cmd.append("--allow-dirty-fingerprint")
                exp_rc, _, exp_err = run_bounded(exp_cmd, timeout_s=15)
                if exp_rc == 0:
                    append_ledger_row(
                        {
                            "timestamp": now_iso,
                            "date": sweep_date,
                            "repo": repo,
                            "digest_status": today_status,
                            "digest_path": "",
                            "worktree": str(wt_dir),
                            "worktree_key": str(wt_dir),
                            "branch": wt_branch,
                            "base_sha": base_sha,
                            "head_sha": head_sha,
                            "lens": lens,
                            "verdict": "EXPIRED",
                            "subreason": "SLA_7D_AUTO_EXPIRE",
                            "ocr_review": "skipped",
                            "coderabbit": "skipped",
                            "lrc": "skipped_policy",
                            "tier1": {"age_days": round(age_days, 2)},
                            "tier2": {
                                "ocr_review": "skipped",
                                "coderabbit": "skipped",
                                "lrc": "skipped_policy",
                            },
                            "lrc_executed": False,
                        }
                    )
                else:
                    judge_degraded = True
                    sys.stderr.write(exp_err or f"[WARN] judge: failed to transition expired worktree {wt_dir} (exit {exp_rc})\n")
            continue

        if bucket == "EXPIRED" and not force_rejudge:
            continue

        # (d) Evaluate UNJUDGED worktree (or all unmerged worktrees under --force-rejudge).
        cand_digest, cand_digest_text = match_candidate_digest(
            repo, wt_dir, wt_branch, base_sha, head_sha, today_digest
        )
        cand_status = parse_digest_field(cand_digest_text, "Status").upper() if cand_digest_text else today_status
        cand_substatus = parse_digest_field(cand_digest_text, "Substatus").upper() if cand_digest_text else ""
        if not meta.get("lens") and cand_digest_text:
            parsed_lens = parse_digest_field(cand_digest_text, "Lens").lower()
            if parsed_lens:
                lens = parsed_lens

        verdict = ""
        subreason = ""
        base_check_escalate = False
        merge_tree_clean = False
        collisions_rc = 0
        ocr_preview_status = "skipped"
        gitnexus_risk = "NONE"
        gitnexus_degraded = False
        verify_env_missing_linter = False
        symbol_test_refs = 0
        files_changed = 0
        files_changed_ok = False
        diff_loc = 0
        diff_loc_measured = False
        open_pr_collisions_checked = False
        ocr_review_ok = False
        ocr_status = "skipped"
        ocr_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        coderabbit_status = "skipped"
        cr_counts = {"critical": 0, "major": 0, "minor": 0, "trivial": 0, "info": 0, "none": 0}
        lrc_status = "skipped_policy"
        lrc_counts = {"critical": 0, "high": 0, "major": 0, "medium": 0, "minor": 0, "low": 0}
        lrc_executed = False
        base_check_verdict = "NOT_NEEDED"

        # Fast deterministic policy & semantic coverage probe (replays exact saved verify overrides for this HEAD).
        verify_cmd = [worktree_sh, "verify", "--worktree", str(wt_dir), "--lens", lens, "--test-cmd", "true"]
        if repo in RESEARCH_REPOS and lens == "bolt":
            verify_cmd.extend(["--numeric-check-cmd", "true"])
        if not dirty and head_sha and meta.get("verify_head_sha") == head_sha:
            if meta.get("verify_allow_test_edits"):
                verify_cmd.append("--allow-test-edits")
            if meta.get("verify_allow_harness_changes"):
                verify_cmd.append("--allow-harness-changes")
            if meta.get("verify_expected_test_count"):
                verify_cmd.extend(["--expected-test-count", str(meta["verify_expected_test_count"])])
        v_rc, v_out, v_err = run_bounded(verify_cmd, timeout_s=60)
        if v_rc == 2 and "No undefined-name checker available" in (v_out + v_err):
            verify_env_missing_linter = True
            verdict = "JUDGE_ESCALATE_HUMAN"
            subreason = "VERIFY_ENV_MISSING_LINTER"
        elif v_rc in (2, 3):
            verdict = "JUDGE_REJECT"
            subreason = "HARNESS_OR_COVERAGE_VIOLATION"
        elif v_rc != 0:
            verdict = "JUDGE_ESCALATE_HUMAN"
            subreason = "VERIFY_UNEXPECTED_ERROR"

        # Base-check classification for provisional GATE_FAILURE digests.
        if not verdict and cand_substatus == "GATE_FAILURE":
            cached_reused = False
            if "## Base-Check Classification" in cand_digest_text:
                bc_block = cand_digest_text.split("## Base-Check Classification", 1)[1].split("\n## ", 1)[0]
                m_bcv = re.search(r"(?im)^\s*-\s*Verdict:\s*([A-Z_]+)", bc_block)
                m_wt = re.search(r"(?im)^\s*-\s*Worktree:\s*(.+)$", bc_block)
                m_fp = re.search(r"(?im)^\s*-\s*Content Fingerprint:\s*([0-9a-f]{64})\b", bc_block)
                wt_matches = bool(
                    m_wt and m_wt.group(1).strip() in (str(wt_dir), os.path.realpath(str(wt_dir)))
                )
                fp_matches = bool(m_fp and eval_fingerprint and m_fp.group(1).strip() == eval_fingerprint)
                if m_bcv and wt_matches and fp_matches:
                    cached_reused = True
                    base_check_verdict = m_bcv.group(1).strip()
                    if base_check_verdict == "CAUSED_BY_CHANGE":
                        verdict = "JUDGE_REJECT"
                        subreason = "BASE_CHECK_CAUSED_BY_CHANGE"
            if not cached_reused:
                bc_cmd = ["bash", ctl_sh, "base-check", "--repo", repo, "--worktree", str(wt_dir)]
                if cand_digest is not None and cand_digest.is_file():
                    bc_cmd.extend(["--digest", str(cand_digest)])
                bc_rc, bc_out, _ = run_bounded(bc_cmd, timeout_s=300)
                m_out = re.search(r"(?m)^VERDICT:\s*([A-Z_]+)$", bc_out)
                if m_out:
                    base_check_verdict = m_out.group(1).strip()
                if bc_rc == 2 or base_check_verdict == "CAUSED_BY_CHANGE":
                    verdict = "JUDGE_REJECT"
                    subreason = "BASE_CHECK_CAUSED_BY_CHANGE"
                elif bc_rc != 0:
                    base_check_escalate = True
                    base_check_verdict = f"EXIT_{bc_rc}"

        # Diff sizing (committed range vs base_sha, pinned to captured head_sha).
        changed_files = []
        diff_target = head_sha or "HEAD"
        if base_sha:
            rc_df, df_out, _ = run_bounded(
                ["git", "-C", str(wt_dir), "diff", "--no-renames", "--name-only", f"{base_sha}..{diff_target}"],
                timeout_s=15,
            )
            if rc_df == 0:
                files_changed_ok = True
                changed_files = [ln.strip() for ln in df_out.splitlines() if ln.strip()]
                files_changed = len(changed_files)
            rc_ns, ns_out, _ = run_bounded(
                ["git", "-C", str(wt_dir), "diff", "--no-renames", "--numstat", f"{base_sha}..{diff_target}"],
                timeout_s=15,
            )
            if rc_ns == 0:
                diff_loc_measured = True
                for ln in ns_out.splitlines():
                    parts = ln.split("\t")
                    if len(parts) >= 2:
                        add_n = int(parts[0]) if parts[0].isdigit() else 0
                        del_n = int(parts[1]) if parts[1].isdigit() else 0
                        diff_loc += add_n + del_n

        # Upstream ref for local merge-tree check.
        upstream_ref = f"origin/{default_branch}"
        rc_ur, _, _ = run_bounded(["git", "-C", str(wt_dir), "rev-parse", "--verify", "--quiet", upstream_ref], timeout_s=10)
        if rc_ur != 0:
            upstream_ref = default_branch
            rc_ur2, _, _ = run_bounded(["git", "-C", str(wt_dir), "rev-parse", "--verify", "--quiet", upstream_ref], timeout_s=10)
            if rc_ur2 != 0 and base_sha:
                upstream_ref = base_sha

        is_sentinel = (lens == "sentinel") or (cand_status == "SECURITY_REPORT_ONLY")

        if not verdict and is_sentinel:
            # Hard Privacy Gate: NEVER invoke cloud reviewers (ocr review, coderabbit, lrc).
            rc_mt, _, _ = run_bounded(["git", "-C", str(wt_dir), "merge-tree", "--write-tree", upstream_ref, diff_target], timeout_s=20)
            merge_tree_clean = rc_mt == 0
            ocr_bin = shutil.which("ocr")
            if ocr_bin and base_sha:
                rc_op, _, _ = run_bounded(
                    [ocr_bin, "delegate", "preview", "--format", "json", "--from", base_sha, "--to", diff_target],
                    cwd=wt_dir,
                    timeout_s=30,
                )
                ocr_preview_status = "ok" if rc_op == 0 else "degraded"
            ocr_status = "skipped_privacy"
            coderabbit_status = "skipped_privacy"
            lrc_status = "skipped_privacy"
            verdict = "JUDGE_ESCALATE_HUMAN"
            subreason = "SECURITY_REPORT_ONLY_LOCAL_BOUNDARY"

        elif not verdict:
            # Tier 1: merge-tree, check-collisions, ocr delegate preview, GitNexus impact.
            rc_mt, _, _ = run_bounded(["git", "-C", str(wt_dir), "merge-tree", "--write-tree", upstream_ref, diff_target], timeout_s=20)
            merge_tree_clean = rc_mt == 0

            if changed_files and wt_repo_dir is not None and is_git_repo(wt_repo_dir):
                if not skip_tier2 and shutil.which("gh") and is_gh_usable_for_repo(wt_repo_dir):
                    col_cmd = [
                        worktree_sh,
                        "check-collisions",
                        "--repo",
                        f"abhimehro/{repo}",
                        "--include-worktrees",
                        "--repo-path",
                        str(wt_repo_dir),
                        "--exclude-worktree",
                        str(wt_dir),
                    ]
                    for cf in changed_files:
                        col_cmd.extend(["--file", cf])
                    collisions_rc, _, _ = run_bounded(col_cmd, timeout_s=60)
                    open_pr_collisions_checked = True
                else:
                    collisions_rc = check_local_worktree_collisions(wt_repo_dir, wt_dir, changed_files)
                    open_pr_collisions_checked = is_local_origin_repo(wt_repo_dir)
            elif not changed_files:
                collisions_rc = 0 if files_changed_ok else 6
                open_pr_collisions_checked = files_changed_ok
            else:
                collisions_rc = 6
                open_pr_collisions_checked = False

            ocr_bin = shutil.which("ocr")
            if ocr_bin and base_sha:
                rc_op, _, _ = run_bounded(
                    [ocr_bin, "delegate", "preview", "--format", "json", "--from", base_sha, "--to", diff_target],
                    cwd=wt_dir,
                    timeout_s=30,
                )
                ocr_preview_status = "ok" if rc_op == 0 else "degraded"

            node_bin = shutil.which("node")
            run_cjs = (wt_repo_dir / ".gitnexus" / "run.cjs") if wt_repo_dir is not None else None
            if node_bin and run_cjs is not None and run_cjs.is_file():
                _, gn_st_out, gn_st_err = run_bounded([node_bin, str(run_cjs), "status"], cwd=wt_repo_dir, timeout_s=20)
                if "stale" in (gn_st_out + gn_st_err).lower() and not skip_tier2 and not gitnexus_refreshed:
                    run_bounded([node_bin, str(run_cjs), "analyze", "--index-only"], cwd=wt_repo_dir, timeout_s=90)
                    gitnexus_refreshed = True
                changed_syms = extract_changed_symbols(wt_dir, base_sha, diff_target) if base_sha else []
                symbol_test_refs = count_symbol_test_references(wt_dir, changed_syms)
                for sym in changed_syms:
                    imp_rc, imp_out, imp_err = run_bounded(
                        [node_bin, str(run_cjs), "impact", sym, "--direction", "upstream", "--repo", str(wt_repo_dir)],
                        cwd=wt_repo_dir,
                        timeout_s=20,
                    )
                    combined_imp = imp_out + "\n" + imp_err
                    matched_risk = False
                    for rk in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"):
                        if re.search(rf'(?i)(?:"risk"\s*:\s*"{rk}"|\brisk\s*[:=]\s*{rk}\b)', combined_imp):
                            matched_risk = True
                            if RISK_ORDER[rk] > RISK_ORDER[gitnexus_risk]:
                                gitnexus_risk = rk
                            break
                    if imp_rc != 0 or not matched_risk:
                        gitnexus_degraded = True
                        if RISK_ORDER["UNKNOWN"] > RISK_ORDER[gitnexus_risk]:
                            gitnexus_risk = "UNKNOWN"

            # Tier 2: ocr review + CodeRabbit + sparing lrc (only when not --skip-tier2 and committed).
            if not skip_tier2 and not dirty and base_sha and head_sha and head_sha != base_sha and not base_check_escalate:
                if ocr_bin:
                    with tempfile.TemporaryDirectory(prefix="proactive-judge-ocr-") as tmp_d:
                        tmp_ocr = pathlib.Path(tmp_d) / "ocr-review.json"
                        ocr_rc, ocr_out, _ = run_bounded(
                            [
                                ocr_bin,
                                "review",
                                "--audience",
                                "agent",
                                "--format",
                                "json",
                                "--from",
                                base_sha,
                                "--to",
                                diff_target,
                                "--output",
                                str(tmp_ocr),
                                "-b",
                                f"Proactive {lens} candidate on abhimehro/{repo}",
                            ],
                            cwd=wt_dir,
                            timeout_s=180,
                        )
                        raw_ocr = ""
                        if tmp_ocr.is_file():
                            raw_ocr = tmp_ocr.read_text(encoding="utf-8", errors="replace")
                        if not raw_ocr.strip():
                            raw_ocr = ocr_out
                        if ocr_rc == 0:
                            parsed_ok, ocr_counts = parse_ocr_review(raw_ocr)
                            ocr_review_ok = parsed_ok
                            ocr_status = "completed" if parsed_ok else "degraded"
                        else:
                            ocr_review_ok = False
                            ocr_status = "degraded"
                else:
                    ocr_review_ok = False
                    ocr_status = "missing"

                cr_bin = shutil.which("coderabbit")
                if cr_bin:
                    au_rc, au_out, au_err = run_bounded([cr_bin, "auth", "status", "--agent"], cwd=wt_dir, timeout_s=20)
                    au_blob = au_out + "\n" + au_err
                    is_authed = False
                    if au_rc == 0:
                        for line in au_blob.splitlines():
                            s = line.strip()
                            if not s:
                                continue
                            try:
                                aobj = json.loads(s)
                                if isinstance(aobj, dict) and aobj.get("authenticated") is True:
                                    is_authed = True
                                    break
                            except json.JSONDecodeError:
                                continue
                        if not is_authed and re.search(r'(?i)"?authenticated"?\s*:\s*true\b', au_blob):
                            is_authed = True
                    if is_authed:
                        cr_rc, cr_out, _ = run_bounded(
                            [cr_bin, "review", "--agent", "--committed", "--base-commit", base_sha],
                            cwd=wt_dir,
                            timeout_s=420,
                        )
                        coderabbit_status, cr_counts = parse_coderabbit_ndjson(cr_out, cr_rc)
                    else:
                        coderabbit_status = "unauthenticated"
                else:
                    coderabbit_status = "missing"

                # Sparing LiveReview (lrc) tie-breaker policy.
                ocr_clean_hi = (ocr_counts["critical"] + ocr_counts["high"]) == 0
                cr_clean_hi = (cr_counts["critical"] + cr_counts["major"]) == 0
                lrc_trigger = (
                    with_lrc
                    or (coderabbit_status != "review_completed" and ocr_clean_hi)
                    or (gitnexus_risk == "HIGH" and cr_clean_hi and ocr_clean_hi)
                )
                lrc_bin = shutil.which("lrc")
                if (
                    lrc_trigger
                    and lrc_bin
                    and diff_loc_measured
                    and bool(base_sha)
                    and bool(head_sha)
                    and diff_loc <= 250
                    and count_daily_lrc_runs(sweep_date) < 1
                ):
                    u_rc, u_out, _ = run_bounded([lrc_bin, "usage", "inspect", "--output", "json"], cwd=wt_dir, timeout_s=20)
                    if u_rc != 0:
                        u_rc, u_out, _ = run_bounded([lrc_bin, "usage", "inspect"], cwd=wt_dir, timeout_s=20)
                    can_trig, rem_loc = parse_lrc_usage(u_out) if u_rc == 0 else (False, None)
                    if can_trig and rem_loc is not None and rem_loc >= 2000:
                        l_rc, l_out, _ = run_bounded(
                            [lrc_bin, "review", "--no-serve", "--output", "json", "--range", f"{base_sha}...{diff_target}"],
                            cwd=wt_dir,
                            timeout_s=180,
                        )
                        lrc_executed = True
                        lrc_status, lrc_counts = parse_lrc_review(l_out, l_rc)
                    else:
                        lrc_status = "skipped_policy"
                else:
                    lrc_status = "skipped_policy"
            elif skip_tier2:
                ocr_status = "skipped_tier2"
                coderabbit_status = "skipped_tier2"
                lrc_status = "skipped_policy"

            # Final verdict rubric for non-rejected, non-sentinel candidates.
            lrc_blocking = lrc_executed and (
                lrc_status != "completed"
                or (lrc_counts["critical"] + lrc_counts["high"] + lrc_counts["major"]) > 0
            )
            untested_critical = (gitnexus_risk == "CRITICAL") and (symbol_test_refs == 0)

            if (
                not dirty
                and head_sha
                and head_sha != base_sha
                and not base_check_escalate
                and merge_tree_clean
                and files_changed_ok
                and collisions_rc == 0
                and open_pr_collisions_checked
                and not skip_tier2
                and not gitnexus_degraded
                and ocr_review_ok
                and (ocr_counts["critical"] + ocr_counts["high"]) == 0
                and coderabbit_status == "review_completed"
                and (cr_counts["critical"] + cr_counts["major"]) == 0
                and not lrc_blocking
                and not untested_critical
            ):
                verdict = "JUDGE_PASS_ROUTINE"
                subreason = "ALL_TIERS_CLEAN"
            else:
                verdict = "JUDGE_ESCALATE_HUMAN"
                if base_check_escalate:
                    subreason = "BASE_CHECK_UNUSABLE"
                elif dirty or not head_sha or head_sha == base_sha:
                    subreason = "DIRTY_UNCOMMITTED_WORKTREE"
                elif not merge_tree_clean:
                    subreason = "UPSTREAM_MERGE_CONFLICT"
                elif collisions_rc != 0 or not files_changed_ok or not open_pr_collisions_checked:
                    subreason = "COLLISION_OR_UNVERIFIABLE"
                elif skip_tier2:
                    subreason = "TIER2_SKIPPED_OFFLINE"
                elif untested_critical:
                    subreason = "CRITICAL_UNTESTED_BLAST_RADIUS"
                elif (
                    (ocr_counts["critical"] + ocr_counts["high"]) > 0
                    or (cr_counts["critical"] + cr_counts["major"]) > 0
                    or (lrc_counts["critical"] + lrc_counts["high"] + lrc_counts["major"]) > 0
                ):
                    subreason = "REVIEWER_FINDINGS_PRESENT"
                elif gitnexus_degraded:
                    subreason = "GITNEXUS_DEGRADED"
                else:
                    subreason = "REVIEWER_DEGRADED_OR_INCOMPLETE"

        # Verify worktree identity did not change mid-evaluation before recording state or retiring.
        mutated_mid_eval = False
        rc_ch, ch_out, _ = run_bounded(["git", "-C", str(wt_dir), "rev-parse", "--verify", "--quiet", "HEAD"], timeout_s=10)
        cur_head_sha = ch_out.strip() if rc_ch == 0 else ""
        cur_fp = compute_wt_content_fingerprint(wt_dir, cur_head_sha) if cur_head_sha else ""
        if (head_sha and cur_head_sha != head_sha) or (eval_fingerprint and cur_fp != eval_fingerprint):
            mutated_mid_eval = True
            verdict = "JUDGE_ESCALATE_HUMAN"
            subreason = "WORKTREE_CHANGED_DURING_EVAL"

        tier1_summary = {
            "verify_probe_rc": v_rc,
            "base_check": base_check_verdict,
            "merge_tree_clean": merge_tree_clean,
            "collisions_rc": collisions_rc,
            "ocr_preview": ocr_preview_status,
            "gitnexus_risk": gitnexus_risk,
            "gitnexus_degraded": gitnexus_degraded,
            "symbol_test_refs": symbol_test_refs,
        }
        tier2_summary = {
            "ocr_review": ocr_status,
            "ocr_counts": ocr_counts,
            "coderabbit": coderabbit_status,
            "coderabbit_counts": cr_counts,
            "lrc": lrc_status,
            "lrc_counts": lrc_counts,
        }

        ledger_entry = {
            "timestamp": now_iso,
            "date": sweep_date,
            "repo": repo,
            "digest_status": cand_status,
            "digest_path": str(cand_digest) if cand_digest else "",
            "worktree": str(wt_dir),
            "worktree_key": str(wt_dir),
            "branch": wt_branch,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "lens": lens,
            "verdict": verdict,
            "subreason": subreason,
            "diff_files": files_changed,
            "diff_loc": diff_loc,
            "ocr_review": ocr_status,
            "coderabbit": coderabbit_status,
            "lrc": lrc_status,
            "tier1": tier1_summary,
            "tier2": tier2_summary,
            "lrc_executed": lrc_executed,
        }
        append_ledger_row(ledger_entry)

        cand_expire_date = EXPIRE_DATE
        age_anchor_str = meta.get("reopened_at") or meta.get("created_at", "")
        if age_anchor_str:
            try:
                anc_date = (
                    dt.datetime.strptime(age_anchor_str, "%Y%m%dT%H%M%SZ")
                    .replace(tzinfo=dt.timezone.utc)
                    .date()
                )
                eff_start = min(anc_date, dt.date.fromisoformat(sweep_date))
                cand_expire_date = (eff_start + dt.timedelta(days=max_age_days)).isoformat()
            except ValueError:
                cand_expire_date = EXPIRE_DATE

        retired_ok = False
        if not mutated_mid_eval:
            if verdict == "JUDGE_REJECT":
                rej_cmd = [
                    worktree_sh,
                    "set-state",
                    "--worktree",
                    str(wt_dir),
                    "--state",
                    "REJECTED",
                    "--verdict",
                    verdict,
                    "--subreason",
                    subreason,
                ]
                if head_sha:
                    rej_cmd.extend(["--expected-head", head_sha])
                rej_rc, _, rej_err = run_bounded(rej_cmd, timeout_s=15)
                if rej_rc == 0 and ledger_path.is_file() and ledger_path.stat().st_size > 0:
                    retired_ok = True
                    if wt_dir.is_dir():
                        if wt_repo_dir is not None and is_git_repo(wt_repo_dir):
                            rm_rc, _, rm_err = run_bounded(
                                ["git", "-C", str(wt_repo_dir), "worktree", "remove", "--force", str(wt_dir)],
                                timeout_s=20,
                            )
                            run_bounded(["git", "-C", str(wt_repo_dir), "worktree", "prune"], timeout_s=15)
                            if rm_rc != 0:
                                retired_ok = False
                                sys.stderr.write(rm_err or f"[WARN] judge: worktree remove failed for {wt_dir} (exit {rm_rc})\n")
                            elif wt_branch.startswith("proactive/"):
                                br_rc, _, br_err = run_bounded(
                                    ["git", "-C", str(wt_repo_dir), "branch", "-D", wt_branch],
                                    timeout_s=15,
                                )
                                if br_rc != 0:
                                    retired_ok = False
                                    sys.stderr.write(br_err or f"[WARN] judge: branch delete failed for {wt_branch} (exit {br_rc})\n")
                        else:
                            retired_ok = False
                            sys.stderr.write(f"[WARN] judge: owning repo unavailable for retiring {wt_dir}\n")
                else:
                    sys.stderr.write(rej_err or f"[WARN] judge: set-state REJECTED failed for {wt_dir} (exit {rej_rc})\n")
                if retired_ok:
                    rejected_now += 1
                else:
                    judge_degraded = True
            else:
                dirty_cleared = dirty and base_check_verdict in ("PRE_EXISTING_ON_BASE", "FLAKE_ON_RETRY", "NO_FAILURE")
                if (not dirty and not verify_env_missing_linter) or dirty_cleared:
                    st_cmd = [
                        worktree_sh,
                        "set-state",
                        "--worktree",
                        str(wt_dir),
                        "--state",
                        "JUDGED",
                        "--verdict",
                        verdict,
                        "--subreason",
                        subreason,
                    ]
                    if head_sha:
                        st_cmd.extend(["--expected-head", head_sha])
                    if dirty_cleared:
                        st_cmd.append("--allow-dirty-fingerprint")
                    st_rc, _, _ = run_bounded(st_cmd, timeout_s=15)
                    if st_rc == 0:
                        judged_now += 1
                    else:
                        judge_degraded = True

        if verdict == "JUDGE_REJECT":
            if retired_ok:
                action_line = f"Action: reject (retired automatically on {sweep_date})"
            else:
                action_line = f"Action: reject (manual worktree removal required on {sweep_date})"
        else:
            action_line = f"Action: promote | reject | expire (default: expire on {cand_expire_date})"

        mt_label = "clean" if merge_tree_clean else "conflict_or_unrun"
        eval_section = (
            "## Judge Evaluation\n\n"
            f"- Date: {sweep_date}\n"
            f"- Verdict: {verdict}\n"
            f"- Subreason: {subreason}\n"
            f"- Worktree: {wt_dir}\n"
            f"- Head SHA: {head_sha}\n"
            f"- Tier 1: verify_probe_rc={v_rc}, base_check={base_check_verdict}, merge_tree={mt_label}, "
            f"collisions_rc={collisions_rc}, gitnexus_risk={gitnexus_risk} (test_refs={symbol_test_refs}), "
            f"ocr_preview={ocr_preview_status}\n"
            f"- Tier 2: ocr_review={ocr_status} (critical={ocr_counts['critical']}, high={ocr_counts['high']}, "
            f"medium={ocr_counts['medium']}, low={ocr_counts['low']}), "
            f"coderabbit={coderabbit_status} (critical={cr_counts['critical']}, major={cr_counts['major']}, "
            f"minor={cr_counts['minor']}, trivial={cr_counts['trivial']}, info={cr_counts['info']}), "
            f"lrc={lrc_status}\n"
            f"- {action_line}"
        )
        append_judge_section_to_digest(cand_digest, eval_section, head_sha)

    # (e) Re-scan remaining live worktrees for accurate post-Judge queue counts.
    rem_wts, _, _ = discover_repo_worktrees(repo, default_repo_dir)
    unjudged_open = 0
    judged_open = 0
    expired_preserved = 0
    for wt_dir in rem_wts:
        if not wt_dir.is_dir():
            continue
        _, meta = read_wt_meta(wt_dir)
        if not is_active_candidate_wt(wt_dir, meta):
            continue
        bkt, _, _, _ = effective_wt_bucket(wt_dir, meta)
        if bkt == "JUDGED":
            judged_open += 1
        elif bkt == "EXPIRED":
            expired_preserved += 1
        else:
            unjudged_open += 1

    print(f"repo={repo}")
    print(f"today_status={today_status}")
    print(f"judged_now={judged_now}")
    print(f"rejected_now={rejected_now}")
    print(f"unjudged_open={unjudged_open}")
    print(f"judged_open={judged_open}")
    print(f"expired_preserved={expired_preserved}")
    print(f"judge_status={'DEGRADED' if judge_degraded else 'OK'}")
PY
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

if "proactive-safety-guard" in data and contains_marker(data["proactive-safety-guard"]):
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
		if [[ ! -L ${dyn_sidecar} ]] && [[ -f ${dyn_sidecar} ]] && [[ -f "${dyn_dir}/${PROACTIVE_MANAGED_MARKER}" ]]; then
			rm -f "${dyn_sidecar}" "${dyn_dir}/user_config.json" "${dyn_dir}/${PROACTIVE_MANAGED_MARKER}"
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
	judge)
		cmd_judge "$@"
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
