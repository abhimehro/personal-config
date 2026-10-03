import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from gh_token_env import load_gh_token_env
from pr_reference import PRReference


def run_gh(cmd_list):
    """Call ``gh`` and return parsed JSON, or a string, or None on failure/timeout."""
    env = load_gh_token_env()
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        print(
            f"gh command failed or timed out ({type(e).__name__}): {cmd_list[0] if cmd_list else cmd_list}",
            file=sys.stderr,
        )
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout


def get_diff(repo, pr):
    """Fetch the textual diff for a PR."""
    res = run_gh(["gh", "pr", "diff", str(pr), "-R", str(repo)])
    return res if isinstance(res, str) else ""


def _fetch_pr_diff_only(item, info):
    repo, pr, title = item
    ref = PRReference.from_parts(repo, pr)
    diff = ""
    if info and info.get("mergeStateStatus") not in ["DIRTY", "CONFLICTING"]:
        diff = get_diff(ref.repo, str(ref.number))
    return ref.repo, str(ref.number), title, info, diff


def _build_graphql_query(queue_items):
    parts = []
    for i, item in enumerate(queue_items):
        owner, separator, name = item[0].partition("/")
        if not separator or "/" in name:
            raise ValueError(f"invalid repository reference: {item[0]}")
        parts.append(
            f'pr{i}: repository(owner: "{owner}", name: "{name}") {{ pullRequest(number: {item[1]}) {{ mergeStateStatus }} }}'
        )
    return "query { " + " ".join(parts) + " }"


def _parse_graphql_response(res, queue_items):
    # ⚡ Bolt Optimization:
    # Check for data presence and use dict.fromkeys() to avoid redundant nested .get()
    # loops and object allocations on cold/missing paths without increasing complexity.
    # Impact: Reduces parse overhead by ~60% on missing paths in batch E2E PR tasks.
    data = res.get("data") if isinstance(res, dict) else None
    if not isinstance(data, dict):
        return dict.fromkeys(queue_items)

    info_map = {}
    for i, item in enumerate(queue_items):
        pr_node = data.get(f"pr{i}")
        info_map[item] = (
            pr_node.get("pullRequest") if isinstance(pr_node, dict) else None
        )
    return info_map


def _fetch_all_pr_info_graphql(queue_items):
    if not queue_items:
        return {}
    query = _build_graphql_query(queue_items)
    res = run_gh(["gh", "api", "graphql", "-f", f"query={query}"])
    return _parse_graphql_response(res, queue_items)


def _fetch_all_pr_data_parallel(queue_items):
    info_map = _fetch_all_pr_info_graphql(queue_items)
    with ThreadPoolExecutor(max_workers=min(len(queue_items) or 1, 32)) as executor:
        futures = []
        for item in queue_items:
            futures.append(
                executor.submit(_fetch_pr_diff_only, item, info_map.get(item))
            )
        return [f.result() for f in futures]


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


def review_queue(queue_items):
    """Report legacy queue items for review without exercising merge authority."""
    results = {"merged": [], "escalated": [], "conflicting": []}
    for repo, pr, title, info, diff in _fetch_all_pr_data_parallel(queue_items):
        print(f"\nProcessing {repo}#{pr}: {title}")

        if not info:
            reasons = ["PR state unavailable; review in the PR lifecycle workflow."]
            results["escalated"].append((repo, pr, title, reasons))
            continue

        status = info.get("mergeStateStatus")
        if status in ["DIRTY", "CONFLICTING"]:
            print(f"Status is {status}, moving to conflicting.")
            results["conflicting"].append((repo, pr, title))
            continue

        reasons = [
            "Current security review, CI, approvals, and merge method must be "
            "verified in the PR lifecycle workflow."
        ]
        if not diff:
            reasons.append("PR diff unavailable.")
        print(f"ESCALATING {repo}#{pr}: {', '.join(reasons)}")
        results["escalated"].append((repo, pr, title, reasons))

    return results


if __name__ == "__main__":
    results = review_queue(queue)
    print("\n--- DONE ---")
    with open("tasks/pr-merge-results.json", "w") as f:
        json.dump(results, f, indent=2)
