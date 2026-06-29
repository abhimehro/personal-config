#!/usr/bin/env python3
# ==============================================================================
# secops_agent.py
# Core technical debt, workflow update, and testing agent runner for SecOps.
# Integrates with the google.antigravity SDK for diagnostic intelligence.
# ==============================================================================
import os
import sys
import argparse
import asyncio
import json
import datetime
import logging
import signal
import time
import subprocess
from pathlib import Path

# Try to import google.antigravity SDK for high-assurance reasoning
try:
    from google.antigravity import Agent, LocalAgentConfig
    HAS_ANTIGRAVITY = True
except ImportError:
    HAS_ANTIGRAVITY = False
    Agent = None
    LocalAgentConfig = None

# Default configurations
DEFAULT_REPOS = [
    "personal-config",
    "ctrld-sync",
    "email-security-pipeline",
    "Seatek_Analysis",
    "Hydrograph_Versus_Seatek_Sensors_Project",
    "series_correction_project_updated"
]
DEV_ROOT = Path(os.path.expanduser("~/dev"))

# History logs
LOG_PIN = Path(os.path.expanduser("~/.workflow-updater-history.log"))
LOG_TRIAGE = Path(os.path.expanduser("~/.backlog-miner-history.log"))
LOG_HEALTH = Path(os.path.expanduser("~/.qa-health-history.log"))

# Standard logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("secops-agent")

# Global variables for rate limit tracing
llm_call_count = 0
MAX_LLM_CALLS = 5

def log_history(log_file: Path, message: str):
    """Appends an audit record to the history logs."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def notify_macos(title: str, message: str):
    """Sends a native macOS desktop notification."""
    escaped_msg = message.replace('"', '\\"')
    escaped_title = title.replace('"', '\\"')
    script = f'display notification "{escaped_msg}" with title "{escaped_title}"'
    subprocess.run(["osascript", "-e", script], capture_output=True)

async def run_timeout(cmd, timeout, cwd=None):
    """Runs a command inside its own process group and kills it if timed out.
    
    This matches the robust PGID-kill behaviour in the original lib/ai_engine.sh.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            preexec_fn=os.setsid if sys.platform != "win32" else None
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return proc.returncode, stdout, stderr
        except asyncio.TimeoutError:
            if sys.platform != "win32":
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                proc.terminate()
            await proc.wait()
            return 124, b"", b"Command timed out"
    except Exception as e:
        return -1, b"", str(e).encode()

# ==============================================================================
# AI DIAGNOSTIC ROUTER (Tiered Fallback)
# ==============================================================================
async def ai_diagnose(prompt: str, log_content: str, verbose: bool = False) -> str:
    """Invokes a tiered AI diagnostic analysis: Antigravity SDK -> Vibe CLI -> Raw log dump.
    
    Capped to MAX_LLM_CALLS to respect rate limits.
    """
    global llm_call_count
    
    # Check if we hit the safe limit of API calls
    if llm_call_count >= MAX_LLM_CALLS:
        logger.warning(f"LLM call limit reached ({MAX_LLM_CALLS}). Falling back directly to raw log.")
        return f"[ai_diagnose] Tier 3 Fallback (LLM limit reached):\n{log_content}"

    llm_call_count += 1
    
    # Tier 1: Google Antigravity SDK
    if HAS_ANTIGRAVITY:
        if verbose:
            logger.info("Attempting diagnostic reasoning using Google Antigravity SDK...")
        try:
            config = LocalAgentConfig(
                system_instructions=(
                    "You are a Senior DevOps and Security-First Engineer. Analyze diagnostic logs, "
                    "identify the root cause, and provide a concise, actionable step-by-step fix."
                )
            )
            async with Agent(config=config) as agent:
                full_prompt = f"{prompt}\n\n--- LOG START ---\n{log_content}\n--- LOG END ---"
                response = await agent.chat(full_prompt)
                response_text = await response.text()
                if response_text and response_text.strip():
                    return f"[ai_diagnose] Tier 1: Antigravity SDK\n{response_text}"
        except Exception as e:
            if verbose:
                logger.error(f"Antigravity SDK call failed: {e}. Falling back to Tier 2 (Vibe).")

    # Tier 2: Mistral Vibe CLI
    vibe_path = shutil_which("vibe") or os.path.expanduser("~/.local/bin/vibe")
    if os.path.exists(vibe_path) or shutil_which("vibe"):
        if verbose:
            logger.info("Attempting diagnostic reasoning using Vibe CLI...")
        vibe_cmd = [
            vibe_path if os.path.exists(vibe_path) else "vibe",
            "-p", f"{prompt}\n\n--- LOG START ---\n{log_content}\n--- LOG END ---",
            "--agent", "auto-approve",
            "--output", "text"
        ]
        rc, out, err = await run_timeout(vibe_cmd, 45)
        if rc == 0 and out:
            out_str = out.decode("utf-8", errors="ignore")
            # Strip PyShim debug prefix lines if present
            cleaned_lines = [l for l in out_str.splitlines() if not l.startswith("[ara-pyshim]")]
            return f"[ai_diagnose] Tier 2: Vibe CLI\n" + "\n".join(cleaned_lines)

    # Tier 3: Raw Log Dump
    if verbose:
        logger.info("Falling back to Tier 3 (Raw log dump).")
    return f"[ai_diagnose] Tier 3 Fallback (No AI service available):\n{log_content}"

def shutil_which(cmd):
    """Simple wrapper in case shutil is not loaded."""
    import shutil
    return shutil.which(cmd)

# ==============================================================================
# PIN TIER (GitHub Actions lockfile updates)
# ==============================================================================
async def check_active_bot_reviews(repo_dir: Path) -> bool:
    """Scans for active PR reviews or PRs created by other automation bots.
    
    Prevents race conditions / collision on GHA workflows.
    """
    # Look for open PRs authored by bots
    cmd = ["gh", "pr", "list", "--json", "author,title"]
    rc, out, _ = await run_timeout(cmd, 30, cwd=repo_dir)
    if rc == 0 and out:
        try:
            prs = json.loads(out)
            for pr in prs:
                author = pr.get("author", {}).get("login", "").lower()
                title = pr.get("title", "").lower()
                if "bot" in author or "jules" in author or "dependabot" in author or "renovate" in author:
                    return True
        except Exception:
            pass
    return False

async def run_pin(args):
    """Executes the Pin Tier updates for Actions dependencies."""
    logger.info("Starting Pin Tier (GHA Workflow Updater)...")
    log_history(LOG_PIN, "START - Pin Tier run begin.")
    
    overall_success = True
    lockfile_path = ".github/aw/actions-lock.json"
    
    for repo in args.repos:
        repo_dir = DEV_ROOT / repo
        if not (repo_dir / ".git").is_dir():
            logger.info(f"skip: {repo} (not a git repo)")
            log_history(LOG_PIN, f"SKIP - {repo} not a git repo.")
            continue
            
        if not (repo_dir / lockfile_path).is_file():
            logger.info(f"skip: {repo} has no {lockfile_path}")
            log_history(LOG_PIN, f"SKIP - {repo} has no actions-lock.json.")
            continue
            
        logger.info(f"==> Pin check: {repo}")
        
        # Check active bot review collision
        if await check_active_bot_reviews(repo_dir):
            logger.info(f"  warn: Active bot PRs detected for {repo}. Skipping to prevent race conditions.")
            log_history(LOG_PIN, f"SKIP - {repo} has active bot reviews/PRs.")
            continue

        if args.dry_run:
            logger.info("  dry-run: skipping gh aw update.")
            log_history(LOG_PIN, f"DRY-RUN - {repo} check complete.")
            continue
            
        # Update lockfile
        update_cmd = ["gh", "aw", "update", "--verbose"]
        rc, out, err = await run_timeout(update_cmd, 300, cwd=repo_dir)
        if rc != 0:
            logger.error(f"  gh aw update failed (rc={rc}) for {repo}")
            log_history(LOG_PIN, f"FAIL - {repo} gh aw update failed.")
            overall_success = False
            continue
            
        # Check if changes exist
        diff_cmd = ["git", "diff", "--quiet", "--", lockfile_path]
        rc, _, _ = await run_timeout(diff_cmd, 15, cwd=repo_dir)
        if rc == 0:
            logger.info("  up to date.")
            log_history(LOG_PIN, f"NO-OP - {repo} workflows up to date.")
            continue
            
        # Safeguard: never commit compiled lock files
        checkout_cmd = ["git", "checkout", "--", ".github/workflows/*.lock.yml"]
        await run_timeout(checkout_cmd, 15, cwd=repo_dir)
        
        # Validate compile
        validate_cmd = ["gh", "aw", "compile", "--validate"]
        v_rc, _, v_err = await run_timeout(validate_cmd, 120, cwd=repo_dir)
        if v_rc != 0:
            logger.error(f"  compile validation FAILED for {repo}. Reverting lockfile.")
            # Revert lockfile to remain clean
            await run_timeout(["git", "checkout", "--", lockfile_path], 15, cwd=repo_dir)
            log_history(LOG_PIN, f"FAIL - {repo} compile validation failed.")
            overall_success = False
            continue
            
        # Commit lockfile
        add_cmd = ["git", "add", lockfile_path]
        await run_timeout(add_cmd, 15, cwd=repo_dir)
        commit_msg = f"chore(deps): update GitHub Actions versions [{datetime.date.today().strftime('%Y-%m-%d')}]"
        commit_cmd = ["git", "commit", "-m", commit_msg]
        c_rc, _, _ = await run_timeout(commit_cmd, 30, cwd=repo_dir)
        if c_rc != 0:
            logger.error(f"  git commit failed for {repo}")
            log_history(LOG_PIN, f"FAIL - {repo} git commit failed.")
            overall_success = False
            continue
            
        # Push with rebase-once safeguard
        push_cmd = ["git", "push", "origin", "main"]
        p_rc, _, _ = await run_timeout(push_cmd, 120, cwd=repo_dir)
        if p_rc != 0:
            logger.warning(f"  Push failed for {repo}. Upstream conflict? Attempting rebase-once.")
            # Attempt git pull --rebase
            pull_rc, _, _ = await run_timeout(["git", "pull", "--rebase"], 120, cwd=repo_dir)
            if pull_rc != 0:
                logger.error(f"  Rebase failed. Aborting.")
                await run_timeout(["git", "rebase", "--abort"], 15, cwd=repo_dir)
                # Rollback commit
                await run_timeout(["git", "reset", "--hard", "HEAD~1"], 15, cwd=repo_dir)
                log_history(LOG_PIN, f"FAIL - {repo} push failed due to rebase merge conflicts.")
                overall_success = False
                continue
                
            # Retry push
            p_rc_retry, _, _ = await run_timeout(push_cmd, 120, cwd=repo_dir)
            if p_rc_retry != 0:
                logger.error(f"  Retry push failed.")
                await run_timeout(["git", "reset", "--hard", "HEAD~1"], 15, cwd=repo_dir)
                log_history(LOG_PIN, f"FAIL - {repo} retry push failed.")
                overall_success = False
                continue
                
        logger.info(f"  Successfully updated and pushed workflows for {repo}")
        log_history(LOG_PIN, f"SUCCESS - {repo} updated action lockfile.")
        
    status_str = "SUCCESS - Pin Tier complete." if overall_success else "PARTIAL - Pin Tier finished with failures."
    log_history(LOG_PIN, status_str)
    return 0 if overall_success else 1

# ==============================================================================
# TRIAGE TIER (Backlog технический debt miner)
# ==============================================================================
async def run_triage(args):
    """Executes the Triage Tier to audit and manage the refactoring backlogs."""
    logger.info("Starting Triage Tier (Backlog Technical Debt Audit)...")
    log_history(LOG_TRIAGE, "START - Triage Tier run begin.")
    
    overall_success = True
    
    for repo in args.repos:
        repo_dir = DEV_ROOT / repo
        if not (repo_dir / ".git").is_dir():
            logger.info(f"skip: {repo} (not a git repo)")
            continue
            
        logger.info(f"==> Triage check: {repo}")
        
        tasks_dir = repo_dir / "tasks"
        lessons_file = tasks_dir / "lessons.md"
        todo_file = tasks_dir / "todo.md"
        
        if not tasks_dir.is_dir() or not todo_file.is_file() or not lessons_file.is_file():
            if args.init_scaffold:
                logger.info(f"  tasks/ directory or scaffolding missing. Initializing for {repo}...")
                if not args.dry_run:
                    tasks_dir.mkdir(parents=True, exist_ok=True)
                    if not todo_file.is_file():
                        todo_file.write_text("# Backlog Tasks\n\n- [ ] Example Initial Technical Debt Task\n")
                    if not lessons_file.is_file():
                        lessons_file.write_text("# Lessons Learned\n\n## Heuristics\n- Maintain strict read/write boundaries.\n")
                    # Commit scaffolding
                    await run_timeout(["git", "add", "tasks/"], 30, cwd=repo_dir)
                    await run_timeout(["git", "commit", "-m", "chore(secops): initialize tasks scaffolding"], 30, cwd=repo_dir)
                    logger.info(f"  Initialized tasks scaffolding in {repo}")
            else:
                logger.info(f"  skip: Scaffolding missing and --init-scaffold not set for {repo}")
                log_history(LOG_TRIAGE, f"SKIP - {repo} tasks scaffolding missing.")
                continue

        # Count open/completed tasks
        todo_content = todo_file.read_text()
        open_count = todo_content.count("- [ ]")
        completed_count = todo_content.count("- [x]")
        
        logger.info(f"  Found {open_count} open and {completed_count} completed tasks in tasks/todo.md")
        log_history(LOG_TRIAGE, f"INFO - {repo}: {open_count} open, {completed_count} completed tasks.")
        
        # Deep technical debt mining analysis if HAS_ANTIGRAVITY
        if HAS_ANTIGRAVITY and not args.dry_run:
            # We can scan repository file layouts to detect Shell scripts missing pipefail, etc.
            # Limit results to args.max_tasks
            issues_found = []
            
            # Simple check: search for shell scripts (*.sh)
            for path in repo_dir.glob("**/*.sh"):
                # Avoid looking inside venv or build directories
                if any(p in path.parts for p in [".venv", "node_modules", "build"]):
                    continue
                try:
                    content = path.read_text()
                    if "set -euo pipefail" not in content and "set -Eeuo pipefail" not in content:
                        issues_found.append({
                            "type": "Refactor",
                            "title": f"Harden shell script {path.relative_to(repo_dir)}",
                            "objective": "Enforce strict error boundaries and pipe-fail safe exits.",
                            "file": str(path.relative_to(repo_dir)),
                            "rationale": "Shell script is missing set -euo pipefail/set -Eeuo pipefail.",
                            "steps": ["Add set -Eeuo pipefail at start of script", "Verify script executes correctly without syntax drift"],
                            "criteria": ["Script has set -Eeuo pipefail", "Run check validates green"]
                        })
                except Exception:
                    pass
                    
            if issues_found:
                tasks_to_add = issues_found[:args.max_tasks]
                added_something = False
                for issue in tasks_to_add:
                    # Formulate issue text
                    task_block = (
                        f"\n### [{issue['type']}] {issue['title']}\n\n"
                        f"- **Objective:** {issue['objective']}\n"
                        f"- **Files Affected:** {issue['file']}\n"
                        f"- **Rationale:** {issue['rationale']}\n"
                        f"- **Suggested Approach:**\n"
                        f"  - " + "\n  - ".join(issue["steps"]) + "\n"
                        f"- **Acceptance Criteria:**\n"
                        f"  - " + "\n  - ".join(issue["criteria"]) + "\n"
                    )
                    # Check if already added
                    if issue["title"] not in todo_content:
                        with open(todo_file, "a") as f:
                            f.write(task_block)
                        logger.info(f"  Added task: {issue['title']}")
                        log_history(LOG_TRIAGE, f"ADDED - {repo}: {issue['title']}")
                        added_something = True
                        
                if added_something:
                    # Commit tasks/todo.md
                    await run_timeout(["git", "add", "tasks/todo.md"], 30, cwd=repo_dir)
                    await run_timeout(["git", "commit", "-m", "chore(secops): append mined technical debt tasks"], 30, cwd=repo_dir)
                    
    log_history(LOG_TRIAGE, "SUCCESS - Backlog structure audit complete.")
    return 0

# ==============================================================================
# HEALTH TIER (QA, Test Run, Configuration Drift Audit)
# ==============================================================================
async def run_repo_tests(repo_dir: Path, timeout: int) -> tuple:
    """Executes the test suite of a target repository based on project patterns."""
    # 1) Makefile checks
    makefile = repo_dir / "Makefile"
    if makefile.is_file():
        content = makefile.read_text()
        if "test-all:" in content:
            return await run_timeout(["make", "test-all"], timeout, cwd=repo_dir)
        elif "test:" in content:
            return await run_timeout(["make", "test"], timeout, cwd=repo_dir)
            
    # 2) package.json checks
    pkg_json = repo_dir / "package.json"
    if pkg_json.is_file():
        try:
            with open(pkg_json) as f:
                data = json.load(f)
            if "test" in data.get("scripts", {}):
                return await run_timeout(["npm", "run", "test", "--", "--watchAll=false"], timeout, cwd=repo_dir)
        except Exception:
            pass
            
    # 3) Python projects
    pyproject = repo_dir / "pyproject.toml"
    req_txt = repo_dir / "requirements.txt"
    pytest_ini = repo_dir / "pytest.ini"
    if pyproject.is_file() or req_txt.is_file() or pytest_ini.is_file():
        local_pytest = repo_dir / ".venv/bin/pytest"
        if local_pytest.is_file() and os.access(local_pytest, os.X_OK):
            return await run_timeout([str(local_pytest)], timeout, cwd=repo_dir)
        elif shutil_which("pytest"):
            return await run_timeout(["pytest"], timeout, cwd=repo_dir)
            
    return 2, b"", b"No tests found"

async def audit_config_drift(verbose: bool) -> tuple:
    """Runs DNS, LaunchAgent and SSH audits and builds a diagnostic log."""
    log_lines = []
    log_lines.append("Auditing system configuration drift...")
    
    # DNS Check
    if shutil_which("scutil"):
        rc, out, _ = await run_timeout(["scutil", "--dns"], 15)
        if rc == 0 and out:
            dns_info = out.decode("utf-8", errors="ignore")
            # Extract nameserver occurrences
            nameservers = [line.strip() for line in dns_info.splitlines() if "nameserver" in line]
            log_lines.append("DNS Configuration nameservers:")
            log_lines.extend(nameservers[:10])
            
    # SSH Check
    ssh_verifier = DEV_ROOT / "personal-config/scripts/verify_ssh_config.sh"
    if ssh_verifier.is_file():
        rc, out, _ = await run_timeout(["bash", str(ssh_verifier)], 30)
        log_lines.append(f"SSH Config Status (rc={rc}):")
        if out:
            log_lines.append(out.decode("utf-8", errors="ignore"))
            
    # LaunchAgent check
    ssh_agent_plist = Path(os.path.expanduser("~/Library/LaunchAgents/com.speedybee.sshkeyrotation.plist"))
    if ssh_agent_plist.is_file():
        rc, out, _ = await run_timeout(["launchctl", "list"], 15)
        if rc == 0 and out:
            if b"com.speedybee.sshkeyrotation" in out:
                log_lines.append("SSH key rotation LaunchAgent: active.")
            else:
                log_lines.append("SSH key rotation LaunchAgent: present but inactive.")
    else:
        log_lines.append("SSH key rotation LaunchAgent: plist missing.")
        
    return "\n".join(log_lines)

async def attempt_auto_fix(repo_dir: Path, err_log: str, confidence_threshold: float) -> bool:
    """Attempts auto-fixing of safe formatting/dependency drift regressions."""
    logger.info(f"Analyzing log for formatting/linting fixes (Confidence threshold={confidence_threshold})...")
    
    # 1. Check for Ruff / Black issues
    if "ruff" in err_log.lower() or "formatter" in err_log.lower() or "style" in err_log.lower():
        # Ruff fix command
        if (repo_dir / ".venv/bin/ruff").is_file():
            fix_cmd = [str(repo_dir / ".venv/bin/ruff"), "check", "--fix", "."]
        elif shutil_which("ruff"):
            fix_cmd = ["ruff", "check", "--fix", "."]
        else:
            return False
            
        logger.info(f"Running autofix command: {' '.join(fix_cmd)}")
        rc, _, _ = await run_timeout(fix_cmd, 60, cwd=repo_dir)
        if rc == 0:
            # Re-run tests once to verify fix
            re_rc, _, _ = await run_repo_tests(repo_dir, 300)
            if re_rc == 0:
                logger.info("Auto-fix successfully resolved test failure! Committing formatter fix.")
                # Commit fix
                await run_timeout(["git", "add", "."], 30, cwd=repo_dir)
                await run_timeout(["git", "commit", "-m", "style(secops): apply automated formatter fixes"], 30, cwd=repo_dir)
                
                # Append audit record to lessons.md
                lessons_file = repo_dir / "tasks/lessons.md"
                if lessons_file.is_file():
                    with open(lessons_file, "a") as lf:
                        lf.write(f"\n- Auto-Applied Formatter Fixes on {datetime.date.today()} to resolve test failure.\n")
                return True
                
    return False

async def run_health(args):
    """Executes the Health Tier daily QA audit and drift detection."""
    logger.info("Starting Health Tier (QA & Drift Audit)...")
    log_history(LOG_HEALTH, "START - Health Tier run begin.")
    
    overall_success = True
    
    # 1. Run Repo Tests
    for repo in args.repos:
        repo_dir = DEV_ROOT / repo
        if not (repo_dir / ".git").is_dir():
            logger.info(f"skip: {repo} (not a git repo)")
            log_history(LOG_HEALTH, f"SKIP - {repo} not a git repo.")
            continue
            
        logger.info(f"==> Testing {repo}...")
        
        # Save output path
        log_out_path = Path(f"/tmp/test_run_{repo}.log")
        
        rc, stdout, stderr = await run_repo_tests(repo_dir, 600)
        log_content = (stdout + stderr).decode("utf-8", errors="ignore")
        log_out_path.write_text(log_content)
        
        if rc == 0:
            logger.info(f"  {repo}: passed.")
            log_history(LOG_HEALTH, f"PASS - {repo}.")
        elif rc == 2:
            logger.info(f"  {repo}: no test path, skipped.")
            log_history(LOG_HEALTH, f"SKIP - {repo} no test path.")
        elif rc == 124:
            logger.error(f"  {repo}: tests TIMED OUT.")
            notify_macos("Health Failure", f"QA tests timed out for {repo}.")
            log_history(LOG_HEALTH, f"TIMEOUT - {repo} exceeded test timeout limits.")
            overall_success = False
        else:
            logger.error(f"  {repo}: tests FAILED (rc={rc}). Running diagnostics.")
            log_history(LOG_HEALTH, f"FAIL - {repo} test regression (rc={rc}).")
            
            # Diagnose failure
            diag_prompt = "Analyze this test failure log, identify the root cause, and provide a concise step-by-step fix. Be brief."
            diag_report = await ai_diagnose(diag_prompt, log_content, verbose=args.verbose)
            logger.info(f"Diagnostic Summary for {repo}:\n{diag_report}")
            
            # Auto-Fix
            if not args.dry_run:
                fixed = await attempt_auto_fix(repo_dir, log_content, args.confidence_threshold)
                if fixed:
                    logger.info("  Auto-fix successfully applied and tests passed.")
                    log_history(LOG_HEALTH, f"FIXED - {repo} automatically healed.")
                else:
                    overall_success = False
                    notify_macos("Health Failure", f"QA tests failed in {repo}.")
            else:
                overall_success = False
                notify_macos("Health Failure", f"QA tests failed in {repo}.")

    # 2. System Drift Check (Strictly report-only)
    logger.info("Running System Drift Check...")
    drift_log = await audit_config_drift(args.verbose)
    
    # Save drift log
    Path("/tmp/drift_audit.log").write_text(drift_log)
    
    if not args.no_llm:
        drift_prompt = (
            "Review this system configuration log. Are there signs of configuration drift, "
            "inactive launch daemons, or DNS leaks? Respond with 'No drift detected' or a short "
            "warning list. Do not suggest applying changes automatically. Be brief."
        )
        drift_report = await ai_diagnose(drift_prompt, drift_log, verbose=args.verbose)
        logger.info(f"Drift Audit Report:\n{drift_report}")
        
    status_str = "SUCCESS - All health checks completed." if overall_success else "PARTIAL - One or more repos failed health tests."
    log_history(LOG_HEALTH, status_str)
    return 0 if overall_success else 1

# ==============================================================================
# MAIN COMMAND DISPATCHER
# ==============================================================================
def run_status(args):
    """Prints recent log history metrics."""
    logger.info("Gathering SecOps Autopilot statuses...")
    for label, log_file in [("Pin", LOG_PIN), ("Triage", LOG_TRIAGE), ("Health", LOG_HEALTH)]:
        if log_file.is_file():
            # Get last 5 lines
            lines = log_file.read_text().splitlines()[-5:]
            logger.info(f"\nRecent [{label}] History Logs:")
            for line in lines:
                logger.info(f"  {line}")
        else:
            logger.info(f"\n[{label}] History Log missing: {log_file}")
    return 0

def main():
    parser = argparse.ArgumentParser(
        description="SecOps Autopilot: technical debt, workflow locking, and health monitoring agent."
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print verbose execution logging.")
    parser.add_argument("--confidence-threshold", type=float, default=0.85, help="Confidence boundary for auto-fixes (default: 0.85).")
    parser.add_argument("--repos", nargs="+", default=DEFAULT_REPOS, help="Repositories to process.")
    
    subparsers = parser.add_subparsers(dest="command", help="Agent subcommands.")
    
    # Subcommand pin
    parser_pin = subparsers.add_parser("pin", help="Pin GHA workflows weekly.")
    parser_pin.add_argument("--dry-run", action="store_true", help="Run checks without modifying/pushing lockfiles.")
    parser_pin.add_argument("--max-retries", type=int, default=1, help="Max push retries on conflicts.")
    
    # Subcommand triage
    parser_triage = subparsers.add_parser("triage", help="Mine technical debt backlog bi-weekly.")
    parser_triage.add_argument("--dry-run", action="store_true", help="Audit backlog statistics without modifications.")
    parser_triage.add_argument("--max-tasks", type=int, default=3, help="Max new tasks appended to todo.md.")
    parser_triage.add_argument("--init-scaffold", action="store_true", help="Auto-initialize tasks/ scaffolding if missing.")
    
    # Subcommand health
    parser_health = subparsers.add_parser("health", help="Execute repository tests and check system drift daily.")
    parser_health.add_argument("--dry-run", action="store_true", help="Audit tests/drift without applying safe format auto-fixes.")
    parser_health.add_argument("--no-llm", action="store_true", help="Skip LLM diagnostic reasoning on logs.")
    
    # Subcommand status
    subparsers.add_parser("status", help="Show history run metrics.")
    
    # Subcommand run (cadence helper for LaunchAgents)
    parser_run = subparsers.add_parser("run", help="Orchestrate runs by LaunchAgent cadences.")
    parser_run.add_argument("--cadence", choices=["weekly", "bi-weekly", "daily"], required=True, help="Trigger cadence.")
    parser_run.add_argument("--dry-run", action="store_true", help="Execute in dry-run mode.")
    parser_run.add_argument("--no-llm", action="store_true", help="Skip LLM diagnostic logs.")
    parser_run.add_argument("--init-scaffold", action="store_true", help="Auto-initialize scaffolding if missing.")

    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Command Router
    loop = asyncio.get_event_loop()
    
    if args.command == "pin":
        sys.exit(loop.run_until_complete(run_pin(args)))
    elif args.command == "triage":
        sys.exit(loop.run_until_complete(run_triage(args)))
    elif args.command == "health":
        sys.exit(loop.run_until_complete(run_health(args)))
    elif args.command == "status":
        sys.exit(run_status(args))
    elif args.command == "run":
        if args.cadence == "weekly":
            # semanal maps to pin GHA workflows
            sys.exit(loop.run_until_complete(run_pin(args)))
        elif args.cadence == "bi-weekly":
            # bi-weekly maps to triage tech debt
            sys.exit(loop.run_until_complete(run_triage(args)))
        elif args.cadence == "daily":
            # daily maps to health/tests
            sys.exit(loop.run_until_complete(run_health(args)))

if __name__ == "__main__":
    main()
