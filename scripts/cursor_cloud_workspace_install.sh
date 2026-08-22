#!/usr/bin/env bash
# Idempotent multi-repo dependency install for Cursor Cloud Agents.
# Sources: .devin/blueprint.yaml per repository + prior dashboard install script.
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PC_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -d "/agent/repos/personal-config" ]]; then
	REPOS_ROOT="/agent/repos"
else
	# Fall back to the parent of personal-config; per-repo installers skip missing siblings.
	REPOS_ROOT="$(cd "${PC_ROOT}/.." && pwd)"
fi

log() {
	printf 'cursor_cloud_workspace_install: %s\n' "$*"
}

pip_user() {
	python3 -m pip install --user --break-system-packages "$@"
}

run_in_repo() {
	local repo="$1"
	shift
	(cd "${repo}" && "$@")
}

restore_editable_egg_info() {
	local repo="$1"
	if [[ ! -d "${repo}/.git" ]]; then
		return 0
	fi
	# Editable installs can rewrite egg-info metadata; restore if the tree is dirty (AGENTS.md).
	if git -C "${repo}" status --porcelain -- '*.egg-info' 2>/dev/null | grep -q .; then
		git -C "${repo}" restore '*.egg-info' 2>/dev/null ||
			git -C "${repo}" checkout -- '*.egg-info' 2>/dev/null ||
			true
	fi
}

ensure_uv() {
	if command -v uv >/dev/null 2>&1; then
		return 0
	fi
	ensure_pip
	log "installing uv via pip (avoids curl|sh installer)"
	pip_user 'uv>=0.5,<0.9'
	export PATH="${HOME}/.local/bin:${PATH}"
}

ensure_pip() {
	if python3 -m pip --version >/dev/null 2>&1; then
		return 0
	fi
	log "bootstrapping pip for python3"
	python3 -m ensurepip --upgrade
	python3 -m pip install --user --upgrade --break-system-packages pip
}

ensure_pipx() {
	export PATH="${HOME}/.local/bin:${PATH}"
	if command -v pipx >/dev/null 2>&1; then
		return 0
	fi
	ensure_pip
	log "installing pipx via pip"
	pip_user pipx
	export PATH="${HOME}/.local/bin:${PATH}"
	if ! command -v pipx >/dev/null 2>&1; then
		log "pipx is still missing after pip install"
		return 1
	fi
}

install_anthropies() {
	if ! ensure_pipx; then
		log "skip anthropies (pipx unavailable)"
		return 0
	fi
	log "installing anthropies CLI via pipx"
	if ! pipx install --force 'git+https://github.com/CharlesHoskinson/anthropies.git'; then
		log "anthropies pipx install failed (non-fatal)"
		return 0
	fi
	export PATH="${HOME}/.local/bin:${PATH}"
	if command -v anthropies >/dev/null 2>&1; then
		anthropies --version || true
	else
		log "anthropies installed but not on PATH"
	fi
}

series27_venv_python_ready() {
	local venv_dir="$1"
	[[ -x "${venv_dir}/bin/python" ]] &&
		"${venv_dir}/bin/python" -c 'import sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 12) else 1)' 2>/dev/null
}

install_personal_config() {
	local repo="${REPOS_ROOT}/personal-config"
	if [[ ! -d ${repo} ]]; then
		log "skip personal-config (missing ${repo})"
		return 0
	fi

	ensure_pip
	log "personal-config: python requirements"
	if [[ -f "${repo}/requirements.txt" ]]; then
		pip_user -r "${repo}/requirements.txt"
	fi

	if [[ -x "${repo}/scripts/install_cursor_cloud_agent_hooks.sh" ]]; then
		log "personal-config: cursor cloud hooks"
		run_in_repo "${repo}" ./scripts/install_cursor_cloud_agent_hooks.sh || true
	fi

	if command -v trunk >/dev/null 2>&1; then
		log "personal-config: trunk launcher already present"
	else
		# SECURITY: skip curl|sh trunk installer (unverified remote script). Cloud agents use
		# make lint-errors for shell correctness; full Trunk is optional on macOS dev machines.
		log "personal-config: skip trunk auto-install (optional; use make lint-errors without Trunk)"
	fi
}

install_ctrld_sync() {
	local repo="${REPOS_ROOT}/ctrld-sync"
	if [[ ! -f "${repo}/pyproject.toml" ]]; then
		log "skip ctrld-sync (no pyproject.toml)"
		return 0
	fi

	ensure_uv
	log "ctrld-sync: uv python 3.13 + sync"
	uv python install 3.13
	uv sync --project "${repo}" --all-extras
	run_in_repo "${repo}" uv run pre-commit install || true
}

install_email_security_pipeline() {
	local repo="${REPOS_ROOT}/email-security-pipeline"
	if [[ ! -f "${repo}/requirements-ci.txt" ]]; then
		log "skip email-security-pipeline (no requirements-ci.txt)"
		return 0
	fi

	ensure_pip
	log "email-security-pipeline: requirements-ci.txt"
	pip_user -r "${repo}/requirements-ci.txt"
	run_in_repo "${repo}" python3 -m pre_commit install || true
}

install_hydrograph() {
	local repo="${REPOS_ROOT}/Hydrograph_Versus_Seatek_Sensors_Project"
	if [[ ! -f "${repo}/requirements-ci.txt" ]]; then
		log "skip Hydrograph (no requirements-ci.txt)"
		return 0
	fi

	ensure_pip
	log "Hydrograph: requirements-ci.txt + editable install"
	pip_user -r "${repo}/requirements-ci.txt"
	pip_user -e "${repo}"
	restore_editable_egg_info "${repo}"
}

install_series_correction() {
	local repo="${REPOS_ROOT}/series_correction_project_updated"
	if [[ ! -f "${repo}/scripts/requirements-dev.txt" ]]; then
		log "skip series_correction (no scripts/requirements-dev.txt)"
		return 0
	fi

	ensure_pip
	log "series_correction: requirements-dev.txt + editable install"
	pip_user -r "${repo}/scripts/requirements-dev.txt"
	pip_user -e "${repo}"
	restore_editable_egg_info "${repo}"
}

install_seatek_analysis() {
	local repo="${REPOS_ROOT}/Seatek_Analysis"
	if [[ ! -f "${repo}/renv.lock" ]]; then
		log "skip Seatek_Analysis (no renv.lock)"
		return 0
	fi

	if ! command -v Rscript >/dev/null 2>&1; then
		log "skip Seatek_Analysis (Rscript not available; install R in Dockerfile)"
		return 0
	fi

	local ppm_repo="https://packagemanager.posit.co/cran/__linux__/noble/latest"
	log "Seatek_Analysis: renv restore (${ppm_repo})"
	if ! (
		set -e
		cd "${repo}"
		# Bootstrap renv into the project library layout renv/activate.R expects; verify with
		# requireNamespace (install.packages returns invisible NULL on success).
		Rscript --no-init-file -e 'lib <- file.path("renv/library", paste0("R-", format(getRversion()[1, 1:2])), R.version$platform); dir.create(lib, recursive = TRUE, showWarnings = FALSE); install.packages("renv", repos = "'"${ppm_repo}"'", lib = lib); if (!requireNamespace("renv", lib.loc = lib, quietly = TRUE)) quit(status = 1)'
		Rscript --no-init-file -e 'lib <- file.path("renv/library", paste0("R-", format(getRversion()[1, 1:2])), R.version$platform); .libPaths(unique(c(lib, .libPaths()))); options(renv.config.repos.override = c(CRAN = "'"${ppm_repo}"'")); renv::restore()'
	); then
		# SECURITY: renv failure must not skip Series 27 — that path is Python-only
		log "Seatek_Analysis: renv restore failed (non-fatal; continuing Series 27 if available)"
	fi

	local series27_venv="${HOME}/.venvs/seatek_series27"
	local python_bin=""
	for candidate in python3.12 python3.11 python3; do
		if command -v "${candidate}" >/dev/null 2>&1 &&
			"${candidate}" -c 'import sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 12) else 1)' 2>/dev/null; then
			python_bin="${candidate}"
			break
		fi
	done

	if [[ -n ${python_bin} && -f "${repo}/Series_27/Analysis/requirements.txt" ]]; then
		log "Seatek_Analysis: optional Series 27 venv"
		if [[ -d ${series27_venv} ]] && ! series27_venv_python_ready "${series27_venv}"; then
			log "Seatek_Analysis: removing stale Series 27 venv"
			rm -rf "${series27_venv}"
		fi
		if [[ ! -d ${series27_venv} ]]; then
			if ! "${python_bin}" -m venv "${series27_venv}"; then
				log "Seatek_Analysis: skip Series 27 venv (python venv unavailable)"
				return 0
			fi
		fi
		if ! "${series27_venv}/bin/python" -m pip --version >/dev/null 2>&1; then
			"${series27_venv}/bin/python" -m ensurepip --upgrade || {
				log "Seatek_Analysis: skip Series 27 venv (pip bootstrap failed)"
				return 0
			}
		fi
		if ! (
			set -e
			"${series27_venv}/bin/python" -m pip install -U pip
			"${series27_venv}/bin/python" -m pip install -r "${repo}/Series_27/Analysis/requirements.txt"
			if [[ -f "${repo}/requirements-dev.txt" ]]; then
				"${series27_venv}/bin/python" -m pip install -r "${repo}/requirements-dev.txt"
			fi
		); then
			log "Seatek_Analysis: Series 27 venv pip install failed (non-fatal)"
		fi
	else
		log "Seatek_Analysis: skip Series 27 venv (no Python 3.11/3.12 or requirements)"
	fi
}

install_repoprompt_ce() {
	local repo="${REPOS_ROOT}/repoprompt-ce"
	if [[ ! -d ${repo} ]]; then
		log "skip repoprompt-ce (missing ${repo})"
		return 0
	fi
	if [[ ! -f "${repo}/Package.swift" ]]; then
		log "skip repoprompt-ce (no Package.swift)"
		return 0
	fi
	log "repoprompt-ce: macOS Swift project — no Linux dependency install (see AGENTS.md / make dev-* on macOS)"
}

log "repos root: ${REPOS_ROOT}"
install_personal_config
install_anthropies
install_ctrld_sync
install_email_security_pipeline
install_hydrograph
install_series_correction
install_seatek_analysis
install_repoprompt_ce
log "done"
