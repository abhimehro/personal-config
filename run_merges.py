from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import time
from functools import lru_cache


def _parse_env_line(line, env_dict):
    line = line.strip()
    if not line:
        return
    if line.startswith("#"):
        return
    if line.startswith("export "):
        line = line[7:].strip()
    # ⚡ Bolt Optimization: Use partition() over split() to avoid intermediate list allocation overhead
    key, sep, val = line.partition("=")
    if not sep:
        return
    env_dict[key] = val.strip("'\"")


@lru_cache(maxsize=None)
def _get_parsed_env_vars():
    # ⚡ Bolt Optimization: Cache only the parsed variables from the file to prevent redundant IO reads, while keeping it safe from mutable dictionary cache poisoning
    parsed_vars = {}
    try:
        with open("../email-security-pipeline/GH_TOKEN.env", "r") as f:
            for line in f:
                _parse_env_line(line, parsed_vars)
    except FileNotFoundError:
        pass
    return parsed_vars


def _load_gh_token_env():
    env = os.environ.copy()
    env.update(_get_parsed_env_vars())
    return env


def run_gh(cmd_list):
    env = _load_gh_token_env()
    result = subprocess.run(cmd_list, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return result.stdout


def get_diff(repo, pr):
    res = run_gh(["gh", "pr", "diff", str(pr), "-R", str(repo)])
    return res if isinstance(res, str) else ""


def _fetch_pr_data(item):
    repo, pr, title = item
    info = run_gh(
        ["gh", "pr", "view", str(pr), "-R", str(repo), "--json", "mergeStateStatus"]
    )
    diff = ""
    if info and info.get("mergeStateStatus") not in ["DIRTY", "CONFLICTING"]:
        diff = get_diff(repo, pr)
    return repo, pr, title, info, diff


def _fetch_all_pr_data_parallel(queue_items):
    # ⚡ Bolt Optimization: Parallelize N+1 read-only API calls using map() to significantly speed up PR data fetching
    # This mitigates network latency and execution time by querying github concurrently
    # ⚡ Bolt Optimization: Dynamic thread concurrency to eliminate batching latency
    with ThreadPoolExecutor(max_workers=min(len(queue_items) or 1, 32)) as executor:
        return list(executor.map(_fetch_pr_data, queue_items))


queue = [
    # SECURITY
    (
        "abhimehro/personal-config",
        "741",
        "🛡️ Sentinel: [HIGH] Fix Option Injection (CWE-88) in pkill/pgrep commands",
    ),
    (
        "abhimehro/ctrld-sync",
        "703",
        "🛡️ Sentinel: [HIGH] Fix SSRF by blocking private IPs",
    ),
    (
        "abhimehro/email-security-pipeline",
        "640",
        "🛡️ Sentinel: [CRITICAL] Fix MITM Vulnerability by Enforcing SSL Verification",
    ),
    (
        "abhimehro/email-security-pipeline",
        "630",
        "🛡️ Sentinel: [MEDIUM] Fix cross-platform file permission handling",
    ),
    (
        "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project",
        "107",
        "🔒 [HIGH] Fix XXE Vulnerability with defusedxml",
    ),
    (
        "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project",
        "104",
        "🔒 Sentinel: [MEDIUM] Add defusedxml dependency to prevent XXE",
    ),
    # CI/INFRA
    (
        "abhimehro/personal-config",
        "738",
        "⚡ Bolt: Cache regex compilations and path matching in repo automation",
    ),
    (
        "abhimehro/personal-config",
        "733",
        "chore: Automated Daily QA & Cleanup of Scratchpads",
    ),
    (
        "abhimehro/personal-config",
        "730",
        "chore(actions): consolidate workflow automation",
    ),
    ("abhimehro/ctrld-sync", "706", "chore: update ruff config to use lint section"),
    (
        "abhimehro/ctrld-sync",
        "700",
        "⚡ Bolt: [performance improvement] Pre-compile regex for profile URL extraction",
    ),
    (
        "abhimehro/email-security-pipeline",
        "632",
        "chore(actions): consolidate workflow automation",
    ),
    (
        "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project",
        "102",
        "chore(actions): consolidate workflow automation",
    ),
    # PERFORMANCE/REFACTOR/UI/FEATURE
    (
        "abhimehro/personal-config",
        "744",
        "⚡ Bolt: [performance improvement] optimize staleness_days parsing overhead",
    ),
    ("abhimehro/personal-config", "743", "Add Cloud agents starter skill (runbook)"),
    (
        "abhimehro/personal-config",
        "740",
        "🎨 Palette: Improve CLI screen reader accessibility by disabling ANSI codes in non-TTY",
    ),
    (
        "abhimehro/ctrld-sync",
        "707",
        "UX: Retain success message and links in no-color mode",
    ),
    (
        "abhimehro/email-security-pipeline",
        "642",
        "⚡ Bolt: [performance improvement] Optimize character filtering in sanitization",
    ),
    (
        "abhimehro/email-security-pipeline",
        "639",
        "🎨 Palette: Add visual symbols to configuration statuses",
    ),
    (
        "abhimehro/Seatek_Analysis",
        "127",
        "⚡ Bolt: Optimize file extension check using tuple with endswith",
    ),
    (
        "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project",
        "108",
        "⚡ Bolt: Optimize already-sorted dataframe sorting overhead",
    ),
]

results = {"merged": [], "escalated": [], "conflicting": []}

if __name__ == '__main__':
    for repo, pr, title, info, diff in _fetch_all_pr_data_parallel(queue):
        print(f"\nProcessing {repo}#{pr}: {title}")

        if not info:
            print("Failed to get info")
            continue

        status = info.get("mergeStateStatus")
        if status in ["DIRTY", "CONFLICTING"]:
            print(f"Status is {status}, moving to conflicting.")
            results["conflicting"].append((repo, pr, title))
            continue

        diff_lower = diff.lower()

        # Gate 2: Security check
        escalate = False
        reasons = []

        for dangerous in ("eval(", "exec(", "dangerouslysetinnerhtml"):
            if dangerous in diff_lower:
                escalate = True
                reasons.append("Dangerous evaluation function detected.")
                break
        if "pull_request_target" in diff_lower and "checkout" in diff_lower:
            escalate = True
            reasons.append("Dangerous GitHub Actions workflow detected.")
        if ".gitignore" in diff_lower and "+" in diff_lower and "!" in diff_lower:
            # Simplistic check for gitignore weakening
            pass
        if ".env.example" in diff_lower and "- " in diff_lower:
            escalate = True
            reasons.append("Weakened .env.example.")

        # ⚡ Bolt Optimization: Cache title.lower() to prevent redundant C-level string allocations during multiple sequential "in" checks
        title_lower = title.lower()
        for sensitive in ("auth", "payment", "migration", "sql"):
            if sensitive in title_lower:
                escalate = True
                reasons.append("Touches sensitive domain (auth/payments/db).")
                break

        if escalate:
            print(f"ESCALATING {repo}#{pr}: {', '.join(reasons)}")
            results["escalated"].append((repo, pr, title, reasons))
            continue

        print(f"Gate 2 passed. Merging...")
        env = _load_gh_token_env()
        res = subprocess.run(
            ["gh", "pr", "merge", str(pr), "-R", str(repo), "--squash", "--delete-branch"],
            capture_output=True,
            text=True,
            env=env,
        )
        if res.returncode == 0:
            print(f"Successfully merged {repo}#{pr}")
            results["merged"].append((repo, pr, title))
        else:
            print(f"Merge failed: {res.stderr}")
            results["escalated"].append(
                (repo, pr, title, ["Merge command failed", res.stderr])
            )
            continue

        print("Waiting 5 seconds for GitHub to update state...")
        time.sleep(5)

        print("\n--- DONE ---")
        with open("tasks/pr-merge-results.json", "w") as f:
            json.dump(results, f, indent=2)
