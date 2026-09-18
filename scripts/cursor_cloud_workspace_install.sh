#!/usr/bin/env bash
# Idempotent multi-repo dependency install for Cursor Cloud Agents.
# Sources: .devin/blueprint.yaml per repository + prior dashboard install script.
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"

# Pin matches the in-session CLI that indexed this workspace. Engines: Node
# ^22.18.0 (see .cursor/Dockerfile). Do not float to @latest.
GITNEXUS_PINNED_VERSION="1.6.12"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PC_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -d "/agent/repos/personal-config" ]]; then
	REPOS_ROOT="/agent/repos"
else
	# Fall back to the parent of personal-config; per-repo installers skip missing siblings.
	REPOS_ROOT="$(cd "${PC_ROOT}/.." && pwd)"
fi

# Write a UTC-timestamped message to stdout and the persistent installer log.
# Resolve the log path at call time so sourced tests can isolate HOME.
log() {
	local message logfile
	logfile="${HOME}/.local/state/cursor-cloud-workspace-install.log"
	message="$(date -u '+%Y-%m-%dT%H:%M:%SZ') cursor_cloud_workspace_install: $*"
	printf '%s\n' "${message}"
	mkdir -p "$(dirname "${logfile}")"
	printf '%s\n' "${message}" >>"${logfile}"
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
		# ${ppm_repo} is intentionally spliced into the single-quoted R code.
		# shellcheck disable=SC2016
		Rscript --no-init-file -e 'lib <- file.path("renv/library", paste0("R-", format(getRversion()[1, 1:2])), R.version$platform); dir.create(lib, recursive = TRUE, showWarnings = FALSE); install.packages("renv", repos = "'"${ppm_repo}"'", lib = lib); if (!requireNamespace("renv", lib.loc = lib, quietly = TRUE)) quit(status = 1)'
		# ${ppm_repo} is intentionally spliced into the single-quoted R code.
		# shellcheck disable=SC2016
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

# Return success when the first three-component version in output matches the pin.
gitnexus_version_matches() {
	local reported="$1" version
	version="$(printf '%s\n' "${reported}" | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || true)"
	[[ ${version} == "${GITNEXUS_PINNED_VERSION}" ]]
}

# SECURITY: launch the pinned CLI with the snapshot Node, not `env node`
# (the live exec-daemon may inject Node 22.14 ahead of /usr/local).
gitnexus_wrap_with_image_node() {
	local js="${HOME}/.local/lib/node_modules/gitnexus/dist/cli/index.js"
	local node_bin="/usr/local/bin/node"
	local dest="${HOME}/.local/bin/gitnexus"
	if [[ -f ${js} && -x ${node_bin} ]]; then
		# NOTE: npm installs the executable as a symlink, so remove it before writing.
		# CAUTION: npm --prefix installs dest as a symlink into dist/cli/index.js.
		# Writing through that symlink overwrites the CLI JS (build log:
		# gitnexus version '' does not match 1.6.12). Replace the link first.
		log "replacing GitNexus wrapper at ${dest} with image-Node wrapper"
		rm -f "${dest}" || return 1
		printf '#!/usr/bin/env bash\nexec %q %q "$@"\n' "${node_bin}" "${js}" >"${dest}" || return 1
		chmod +x "${dest}" || return 1
		# Fail closed if writing somehow still followed a symlink into the CLI.
		if head -n1 "${js}" | grep -Eq '^#!/usr/bin/env bash'; then
			return 1
		fi
		return 0
	fi
	return 0
}

# Add the user CLI directory to PATH and install or verify the pinned GitNexus CLI.
ensure_gitnexus() {
	export PATH="${HOME}/.local/bin:${PATH}"
	local reported=""
	if command -v gitnexus >/dev/null 2>&1; then
		reported="$(gitnexus --version 2>/dev/null || true)"
		if gitnexus_version_matches "${reported}"; then
			log "gitnexus ${GITNEXUS_PINNED_VERSION} already present"
			return 0
		fi
		log "gitnexus present but version '${reported}' != ${GITNEXUS_PINNED_VERSION}; reinstalling"
	fi
	if ! command -v npm >/dev/null 2>&1; then
		log "skip gitnexus (npm not on PATH; needs Node 22.18+ from .cursor/Dockerfile)"
		return 0
	fi
	log "installing gitnexus@${GITNEXUS_PINNED_VERSION} under ${HOME}/.local"
	# SECURITY: pin exact CLI version; --prefix keeps the install in $HOME.
	if ! npm install --global --prefix "${HOME}/.local" "gitnexus@${GITNEXUS_PINNED_VERSION}"; then
		log "gitnexus npm install failed"
		return 1
	fi
	export PATH="${HOME}/.local/bin:${PATH}"
	if ! gitnexus_wrap_with_image_node; then
		log "gitnexus image-Node wrapper failed (CLI entrypoint may be corrupted)"
		return 1
	fi
	if ! command -v gitnexus >/dev/null 2>&1; then
		log "gitnexus installed but not on PATH"
		return 1
	fi
	reported="$(gitnexus --version 2>/dev/null || true)"
	if ! gitnexus_version_matches "${reported}"; then
		log "gitnexus version '${reported}' does not match ${GITNEXUS_PINNED_VERSION}"
		return 1
	fi
	gitnexus --version || true
}

# Append the GitNexus index path once to a Git repository's local exclusions.
exclude_gitnexus_index() {
	local repo="$1"
	local exclude_dir exclude_file
	if [[ ! -d "${repo}/.git" ]]; then
		return 0
	fi
	exclude_dir="${repo}/.git/info"
	exclude_file="${exclude_dir}/exclude"
	mkdir -p "${exclude_dir}"
	if [[ -f ${exclude_file} ]] && grep -qxF '.gitnexus/' "${exclude_file}"; then
		return 0
	fi
	printf '%s\n' '.gitnexus/' >>"${exclude_file}"
}

# Return success only for repository names excluded from cloud indexing.
should_skip_gitnexus_index() {
	local name="$1"
	# NOTE: HOLD_PLATFORM: 16GB Linux cloud VMs OOM (~12GB heap) on this Swift tree.
	[[ ${name} == "repoprompt-ce" ]]
}

# Best-effort index available sibling repositories without generated docs or FTS.
index_gitnexus_repos() {
	if ! command -v gitnexus >/dev/null 2>&1; then
		log "skip gitnexus index (cli missing)"
		return 0
	fi
	local repo name
	for repo in \
		"${REPOS_ROOT}/personal-config" \
		"${REPOS_ROOT}/ctrld-sync" \
		"${REPOS_ROOT}/email-security-pipeline" \
		"${REPOS_ROOT}/Hydrograph_Versus_Seatek_Sensors_Project" \
		"${REPOS_ROOT}/Seatek_Analysis" \
		"${REPOS_ROOT}/series_correction_project_updated" \
		"${REPOS_ROOT}/repoprompt-ce"; do
		name="${repo##*/}"
		if [[ ! -d ${repo} ]]; then
			log "gitnexus: skip ${name} (missing)"
			continue
		fi
		if should_skip_gitnexus_index "${name}"; then
			log "gitnexus: skip ${name} (OOM on Linux cloud VMs; HOLD_PLATFORM)"
			continue
		fi
		if ! exclude_gitnexus_index "${repo}"; then
			log "gitnexus: skip ${name} (cannot update Git exclusion)"
			continue
		fi
		log "gitnexus: analyze --index-only --skip-fts ${name}"
		# --index-only: do not rewrite AGENTS.md / skills. --skip-fts: Ladybug
		# FTS is optional and not installed in the snapshot.
		if ! run_in_repo "${repo}" gitnexus analyze --index-only --skip-fts; then
			log "gitnexus: analyze failed for ${name} (non-fatal)"
		fi
	done
}

# Install supported sibling dependencies, require GitNexus, and index repositories.
cursor_cloud_workspace_install_main() {
	log "repos root: ${REPOS_ROOT}"
	install_personal_config
	install_anthropies
	install_ctrld_sync
	install_email_security_pipeline
	install_hydrograph
	install_series_correction
	install_seatek_analysis
	install_repoprompt_ce
	ensure_gitnexus
	index_gitnexus_repos
	log "done"
}

if [[ ${BASH_SOURCE[0]} == "${0}" ]]; then
	cursor_cloud_workspace_install_main "$@"
fi
