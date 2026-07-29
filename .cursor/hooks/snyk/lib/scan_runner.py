#!/usr/bin/env python3
"""
Scan Runner Module
==================

Manages background Snyk CLI scans: launching the scan_worker.py subprocess,
polling for completion, SARIF result parsing, and reading results.

The afterFileEdit hook calls launch_background_scan() to start a scan.
Throttling is natural: is_scan_running() prevents duplicate launches.

The Stop hook calls wait_for_scan() which polls for the completion marker,
then reads results (including parsed vulnerabilities) from scan.done.
"""

import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# =============================================================================
# CONFIGURATION
# =============================================================================

SCAN_WAIT_TIMEOUT = 90
POLL_INTERVAL_INITIAL = 1.0
POLL_INTERVAL_MAX = 3.0
PID_STALENESS_TIMEOUT = 600

LogFn = Callable[[object], None]


# =============================================================================
# CACHE DIRECTORY MANAGEMENT
# =============================================================================


def get_cache_dir(workspace: str) -> str:
    workspace_hash = hashlib.sha256(workspace.encode()).hexdigest()[:8]
    return os.path.join(tempfile.gettempdir(), f"cursor-sai-{workspace_hash}")


def ensure_cache_dirs(workspace: str) -> str:
    cache_dir = get_cache_dir(workspace)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


# =============================================================================
# SCAN STATE MANAGEMENT
# =============================================================================


def get_scan_pid_file(workspace: str) -> str:
    return os.path.join(get_cache_dir(workspace), "scan.pid")


def get_scan_done_file(workspace: str) -> str:
    return os.path.join(get_cache_dir(workspace), "scan.done")


def is_scan_running(workspace: str) -> bool:
    pid_file = get_scan_pid_file(workspace)
    if not os.path.exists(pid_file):
        return False

    try:
        age = time.time() - os.path.getmtime(pid_file)
        if age > PID_STALENESS_TIMEOUT:
            _cleanup_pid_file(workspace)
            return False
    except OSError:
        pass

    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, OSError):
        _cleanup_pid_file(workspace)
        return False


def is_scan_complete(workspace: str) -> bool:
    return os.path.exists(get_scan_done_file(workspace))


def _cleanup_pid_file(workspace: str) -> None:
    pid_file = get_scan_pid_file(workspace)
    if os.path.exists(pid_file):
        try:
            os.remove(pid_file)
        except OSError:
            pass


# =============================================================================
# SARIF PARSING
# =============================================================================


def _severity_from_priority_score(score: int) -> str:
    if score >= 700:
        return "critical"
    if score >= 500:
        return "high"
    if score >= 300:
        return "medium"
    return "low"


def _severity_from_sarif_result(result: Dict[str, Any]) -> str:
    level = result.get("level", "warning")
    severity = {"error": "high", "warning": "medium", "note": "low"}.get(level, "medium")
    properties = result.get("properties", {})
    if "priorityScore" not in properties:
        return severity
    return _severity_from_priority_score(properties["priorityScore"])


def _cwe_from_properties(properties: Dict[str, Any]) -> Optional[str]:
    cwe_list = properties.get("cwe", ())
    return cwe_list[0] if cwe_list else None


def _vuln_from_location(
    result: Dict[str, Any],
    loc: Dict[str, Any],
    severity: str,
    cwe: Optional[str],
) -> Dict[str, Any]:
    rule_id = result.get("ruleId", "unknown")
    message = result.get("message", {}).get("text", "")
    phys_loc = loc.get("physicalLocation", {})
    artifact = phys_loc.get("artifactLocation", {})
    region = phys_loc.get("region", {})
    start_line = region.get("startLine", 0)
    return {
        "id": rule_id,
        "title": rule_id.replace("/", " - ").replace("_", " ").title(),
        "severity": severity,
        "cwe": cwe,
        "file_path": artifact.get("uri", "unknown"),
        "start_line": start_line,
        "end_line": region.get("endLine", start_line),
        "message": message,
    }


def _vulns_from_sarif_result(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    severity = _severity_from_sarif_result(result)
    cwe = _cwe_from_properties(result.get("properties", {}))
    return [
        _vuln_from_location(result, loc, severity, cwe)
        for loc in result.get("locations", ())
    ]


def parse_sarif_results(json_output: str) -> List[Dict[str, Any]]:
    """Parse Snyk Code SARIF JSON output into a list of vulnerability dicts."""
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError:
        return []

    vulnerabilities: List[Dict[str, Any]] = []
    for run in data.get("runs", ()):
        for result in run.get("results", ()):
            vulnerabilities.extend(_vulns_from_sarif_result(result))
    return vulnerabilities


# =============================================================================
# PATH RESOLUTION
# =============================================================================


def _augment_path_for_snyk(env: Dict[str, str]) -> None:
    """Ensure the snyk binary is discoverable on PATH.

    IDE-spawned subprocesses often lack shell profile additions (nvm, volta).
    Probes common install locations and appends the matching bin directory.
    """
    if shutil.which("snyk", path=env.get("PATH", "")):
        return

    candidates: List[str] = []

    nvm_dir = env.get("NVM_DIR", os.path.expanduser("~/.nvm"))
    nvm_node_bins = sorted(
        glob.glob(os.path.join(nvm_dir, "versions", "node", "*", "bin")),
        reverse=True,
    )
    candidates.extend(nvm_node_bins)

    volta_bin = os.path.expanduser("~/.volta/bin")
    candidates.append(volta_bin)

    candidates.extend(["/usr/local/bin", "/opt/homebrew/bin"])

    for bin_dir in candidates:
        if os.path.isfile(os.path.join(bin_dir, "snyk")):
            env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
            return


# =============================================================================
# AUTH TOKEN RESOLUTION
# =============================================================================


def _ensure_snyk_token(env: Dict[str, str]) -> None:
    """Inject SNYK_TOKEN into env from the Snyk CLI config file if available.

    Covers legacy API-key auth (``api`` field) so the worker subprocess
    doesn't depend on the snyk binary to resolve the token.  OAuth tokens
    (``INTERNAL_OAUTH_TOKEN_STORAGE``) are read natively by the CLI from
    the config file and don't need to be passed via env.
    """
    if env.get("SNYK_TOKEN"):
        return

    config_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    config_path = os.path.join(config_dir, "configstore", "snyk.json")
    try:
        with open(config_path) as f:
            config = json.load(f)
        api_key = config.get("api")
        if api_key and isinstance(api_key, str):
            env["SNYK_TOKEN"] = api_key
    except (OSError, json.JSONDecodeError, FileNotFoundError):
        pass


# =============================================================================
# BACKGROUND SCAN LAUNCHER
# =============================================================================


def launch_background_scan(workspace: str) -> bool:
    """Launch a background Snyk code scan as a detached subprocess.
    PID file is written by the launcher to close the race window."""
    ensure_cache_dirs(workspace)

    if is_scan_running(workspace):
        return False

    done_file = get_scan_done_file(workspace)
    if os.path.exists(done_file):
        os.remove(done_file)

    worker_script = str(Path(__file__).parent.resolve() / "scan_worker.py")
    env = os.environ.copy()
    _augment_path_for_snyk(env)
    _ensure_snyk_token(env)
    env["SAI_WORKSPACE"] = workspace
    env["SAI_CACHE_DIR"] = get_cache_dir(workspace)
    env["SAI_LIB_DIR"] = str(Path(__file__).parent.resolve())

    try:
        proc = subprocess.Popen(
            [sys.executable, worker_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            cwd=workspace,
            env=env,
        )
        pid_file = get_scan_pid_file(workspace)
        with open(pid_file, "w") as f:
            f.write(str(proc.pid))
        return True
    except Exception:
        return False


# =============================================================================
# SCAN COMPLETION
# =============================================================================


def _read_scan_status(workspace: str) -> Optional[str]:
    done_file = get_scan_done_file(workspace)
    try:
        with open(done_file) as f:
            data = json.load(f)
        return data.get("status", "unknown")
    except (OSError, json.JSONDecodeError, FileNotFoundError):
        return None


def get_scan_completion_info(workspace: str) -> Optional[Dict[str, Any]]:
    """Read the full scan.done record (status, started_at, vulnerabilities)."""
    done_file = get_scan_done_file(workspace)
    try:
        with open(done_file) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, FileNotFoundError):
        return None


def _noop_log(_msg: object) -> None:
    return


def _start_scan_if_needed(workspace: str) -> Optional[str]:
    """If no scan is active, launch one. Return a terminal status if launch fails."""
    if is_scan_running(workspace) or is_scan_complete(workspace):
        return None
    if launch_background_scan(workspace):
        return None
    if is_scan_complete(workspace):
        return _read_scan_status(workspace)
    return "unavailable"


def _poll_until_complete(
    workspace: str,
    timeout: float,
    log_fn: LogFn,
) -> Optional[str]:
    start_time = time.time()
    poll_interval = POLL_INTERVAL_INITIAL

    while (time.time() - start_time) < timeout:
        if is_scan_complete(workspace):
            elapsed = time.time() - start_time
            log_fn(f"[SAI] Scan completed ({elapsed:.1f}s)")
            return _read_scan_status(workspace)

        if not is_scan_running(workspace) and not is_scan_complete(workspace):
            log_fn("[SAI] Scan process terminated unexpectedly")
            return None

        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.5, POLL_INTERVAL_MAX)

    log_fn(f"[SAI] Scan timed out after {timeout:.0f}s")
    return None


def wait_for_scan(
    workspace: str,
    timeout: float = SCAN_WAIT_TIMEOUT,
    log_fn: Optional[LogFn] = None,
) -> Optional[str]:
    """Wait for a background scan to complete. Returns the status string
    or None if the wait timed out."""
    logger = log_fn or _noop_log

    if is_scan_complete(workspace):
        return _read_scan_status(workspace)

    launch_status = _start_scan_if_needed(workspace)
    if launch_status == "unavailable":
        return None
    if launch_status is not None:
        return launch_status

    logger("[SAI] Waiting for security scan to complete...")
    return _poll_until_complete(workspace, timeout, logger)


def clear_scan_state(workspace: str) -> None:
    """Clear scan state files (PID, done marker)."""
    for file_path in [get_scan_pid_file(workspace), get_scan_done_file(workspace)]:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
