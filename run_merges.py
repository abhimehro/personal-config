import subprocess
import json
import time
import os

def _parse_env_line(line, env_dict):
    line = line.strip()
    if not line:
        return
    if line.startswith("#"):
        return
    if line.startswith("export "):
        line = line[7:].strip()
    if "=" not in line:
        return
    key, val = line.split("=", 1)
    env_dict[key] = val.strip("'\"")

def _load_gh_token_env():
    env = os.environ.copy()
    try:
        with open("../email-security-pipeline/GH_TOKEN.env", "r") as f:
            for line in f:
                _parse_env_line(line, env)
    except FileNotFoundError:
        pass
    return env

def run_gh(args):
    env = _load_gh_token_env()
    env["GH_PAGER"] = "cat"
    cmd = ["gh"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return result.stdout

def get_diff(repo, pr):
    env = _load_gh_token_env()
    env["GH_PAGER"] = "cat"
    cmd = ["gh", "pr", "diff", str(pr), "-R", str(repo)]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.stdout

def _check_dangerous_code(diff_lower):
    reasons = []
    if "eval(" in diff_lower: reasons.append("eval() detected")
    if "exec(" in diff_lower: reasons.append("exec() detected")
    if "dangerouslysetinnerhtml" in diff_lower: reasons.append("dangerouslySetInnerHTML detected")
    return reasons

def _check_dangerous_actions(diff_lower):
    if "pull_request_target" in diff_lower and "checkout" in diff_lower:
        return ["Dangerous GitHub Actions workflow (pull_request_target + checkout)"]
    return []

def _check_sensitive_domains(title):
    t_lower = title.lower()
    reasons = []
    if "auth" in t_lower: reasons.append("Touches auth domain")
    if "payment" in t_lower: reasons.append("Touches payment domain")
    if "migration" in t_lower: reasons.append("Touches migration domain")
    if "sql" in t_lower: reasons.append("Touches SQL domain")
    return reasons

def check_security_gate(repo, pr, title, diff):
    diff_lower = diff.lower()
    reasons = []
    reasons.extend(_check_dangerous_code(diff_lower))
    reasons.extend(_check_dangerous_actions(diff_lower))

    if ".env.example" in diff_lower and "- " in diff_lower:
        reasons.append("Weakened .env.example")

    reasons.extend(_check_sensitive_domains(title))
    return reasons

def merge_pr(repo, pr):
    print(f"Gate 2 passed. Merging...")
    env = _load_gh_token_env()
    env["GH_PAGER"] = "cat"
    cmd = ["gh", "pr", "merge", str(pr), "-R", str(repo), "--squash", "--delete-branch"]
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return res

def process_queue_item(repo, pr, title):
    print(f"\nProcessing {repo}#{pr}: {title}")

    info = run_gh(["pr", "view", str(pr), "-R", str(repo), "--json", "mergeStateStatus"])
    if not info:
        return "failed_info", None

    status = info.get('mergeStateStatus')
    if status == 'DIRTY' or status == 'CONFLICTING':
        return "conflicting", None

    diff = get_diff(repo, pr)
    reasons = check_security_gate(repo, pr, title, diff)
    if reasons:
        return "escalated", reasons

    res = merge_pr(repo, pr)
    if res.returncode == 0:
        return "merged", None
    return "error", [res.stderr]

def main():
    queue = [
        # SECURITY
        ("abhimehro/personal-config", "741", "🛡️ Sentinel: [HIGH] Fix Option Injection (CWE-88) in pkill/pgrep commands"),
        ("abhimehro/ctrld-sync", "703", "🛡️ Sentinel: [HIGH] Fix SSRF by blocking private IPs"),
        ("abhimehro/email-security-pipeline", "640", "🛡️ Sentinel: [CRITICAL] Fix MITM Vulnerability by Enforcing SSL Verification"),
        ("abhimehro/email-security-pipeline", "630", "🛡️ Sentinel: [MEDIUM] Fix cross-platform file permission handling"),
        ("abhimehro/Hydrograph_Versus_Seatek_Sensors_Project", "107", "🔒 [HIGH] Fix XXE Vulnerability with defusedxml"),
        ("abhimehro/Hydrograph_Versus_Seatek_Sensors_Project", "104", "🔒 Sentinel: [MEDIUM] Add defusedxml dependency to prevent XXE"),

        # CI/INFRA
        ("abhimehro/personal-config", "738", "⚡ Bolt: Cache regex compilations and path matching in repo automation"),
        ("abhimehro/personal-config", "733", "chore: Automated Daily QA & Cleanup of Scratchpads"),
        ("abhimehro/personal-config", "730", "chore(actions): consolidate workflow automation"),
        ("abhimehro/ctrld-sync", "706", "chore: update ruff config to use lint section"),
        ("abhimehro/ctrld-sync", "700", "⚡ Bolt: [performance improvement] Pre-compile regex for profile URL extraction"),
        ("abhimehro/email-security-pipeline", "632", "chore(actions): consolidate workflow automation"),
        ("abhimehro/Hydrograph_Versus_Seatek_Sensors_Project", "102", "chore(actions): consolidate workflow automation"),

        # PERFORMANCE/REFACTOR/UI/FEATURE
        ("abhimehro/personal-config", "744", "⚡ Bolt: [performance improvement] optimize staleness_days parsing overhead"),
        ("abhimehro/personal-config", "743", "Add Cloud agents starter skill (runbook)"),
        ("abhimehro/personal-config", "740", "🎨 Palette: Improve CLI screen reader accessibility by disabling ANSI codes in non-TTY"),
        ("abhimehro/ctrld-sync", "707", "UX: Retain success message and links in no-color mode"),
        ("abhimehro/email-security-pipeline", "642", "⚡ Bolt: [performance improvement] Optimize character filtering in sanitization"),
        ("abhimehro/email-security-pipeline", "639", "🎨 Palette: Add visual symbols to configuration statuses"),
        ("abhimehro/Seatek_Analysis", "127", "⚡ Bolt: Optimize file extension check using tuple with endswith"),
        ("abhimehro/Hydrograph_Versus_Seatek_Sensors_Project", "108", "⚡ Bolt: Optimize already-sorted dataframe sorting overhead")
    ]

    results = {'merged': [], 'escalated': [], 'conflicting': []}

    for repo, pr, title in queue:
        outcome, reasons = process_queue_item(repo, pr, title)
        
        if outcome == "merged":
            print(f"Successfully merged {repo}#{pr}")
            results['merged'].append((repo, pr, title))
            time.sleep(5)
        elif outcome == "conflicting":
            print(f"Status is DIRTY/CONFLICTING, moving to conflicting.")
            results['conflicting'].append((repo, pr, title))
        elif outcome == "escalated":
            print(f"ESCALATING {repo}#{pr}: {', '.join(reasons)}")
            results['escalated'].append((repo, pr, title, reasons))
        elif outcome == "error":
            print(f"Merge failed: {reasons[0]}")
            results['escalated'].append((repo, pr, title, ["Merge command failed", reasons[0]]))
        elif outcome == "failed_info":
            print("Failed to get info")

    print("\n--- DONE ---")
    with open('tasks/pr-merge-results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
