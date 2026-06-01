import concurrent.futures
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


def _check_security(diff_lower, title_lower):
    reasons = [
        msg for cond, msg in [
            (any(k in diff_lower for k in ("eval(", "exec(", "dangerouslysetinnerhtml")), "Dangerous evaluation function detected."),
            ("pull_request_target" in diff_lower and "checkout" in diff_lower, "Dangerous GitHub Actions workflow detected."),
            (".env.example" in diff_lower and "- " in diff_lower, "Weakened .env.example."),
            (any(k in title_lower for k in ("auth", "payment", "migration", "sql")), "Touches sensitive domain (auth/payments/db)."),
        ]
        if cond
    ]
    return bool(reasons), reasons


def process_pr(repo, pr, title):
    print(f"\nProcessing {repo}#{pr}: {title}")

    # Re-check status
    info = run_gh(
        ["gh", "pr", "view", str(pr), "-R", str(repo), "--json", "mergeStateStatus"]
    )
    if not info:
        print("Failed to get info")
        return "failed", repo, pr, title, None

    status = info.get("mergeStateStatus")
    if status in ["DIRTY", "CONFLICTING"]:
        print(f"Status is {status}, moving to conflicting.")
        return "conflicting", repo, pr, title, None

    diff = get_diff(repo, pr)

    # Gate 2: Security check
    escalate, reasons = _check_security(diff.lower(), title.lower())

    if escalate:
        print(f"ESCALATING {repo}#{pr}: {', '.join(reasons)}")
        return "escalated", repo, pr, title, reasons

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
        print("Waiting 5 seconds for GitHub to update state...")
        time.sleep(5)
        return "merged", repo, pr, title, None
    else:
        print(f"Merge failed: {res.stderr}")
        return "escalated", repo, pr, title, ["Merge command failed", res.stderr]

results = {"merged": [], "escalated": [], "conflicting": []}

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(process_pr, repo, pr, title) for repo, pr, title in queue
    ]
    for future in futures:
        res_type, repo, pr, title, reasons = future.result()
        if res_type == "merged":
            results["merged"].append((repo, pr, title))
        elif res_type == "conflicting":
            results["conflicting"].append((repo, pr, title))
        elif res_type == "escalated":
            results["escalated"].append((repo, pr, title, reasons))

print("\n--- DONE ---")
with open("tasks/pr-merge-results.json", "w") as f:
    json.dump(results, f, indent=2)
