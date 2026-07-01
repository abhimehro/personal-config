import concurrent.futures
from pathlib import Path
import json
import os


def _is_allowlist_rule(rule):
    """Helper to efficiently check if a rule is an allowlist rule."""
    if "PK" not in rule:
        return False
    if "action" not in rule:
        return False
    action = rule["action"]
    if type(action) is not dict:
        return False
    if "do" not in action:
        return False
    return action["do"] == 1


def extract_domains_from_file(filepath):
    """Extract domains from a JSON file."""
    domains = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "rules" in data:
                domains = [rule["PK"] for rule in data["rules"] if "PK" in rule]
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return domains


def extract_allowlist_domains_from_file(filepath):
    """Extract allowlist domains (do: 1) from a JSON file."""
    domains = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "rules" in data:
                # ⚡ Bolt Optimization: Use helper function and list comprehension
                # to balance performance and CodeScene cyclomatic complexity limits
                domains = [
                    rule["PK"] for rule in data["rules"] if _is_allowlist_rule(rule)
                ]
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return domains


def process_denylist_files(base_dir):
    # Tracker files for denylist
    tracker_files = [
        "CD-Microsoft-Tracker.json",
        "CD-No-Safesearch-Support.json",
        "CD-OPPO_Realme-Tracker.json",
        "CD-Roku-Tracker.json",
        "CD-Samsung-Tracker.json",
        "CD-Tiktok-Tracker---aggressive.json",
        "CD-Vivo-Tracker.json",
        "CD-Xiaomi-Tracker.json",
        "CD-Amazon-Tracker.json",
        "CD-Apple-Tracker.json",
        "CD-Badware-Hoster.json",
        "CD-LG-webOS-Tracker.json",
        "CD-Huawei-Tracker.json",
    ]

    print("Extracting denylist domains...")
    denylist_domains = set()

    filepaths = [
        os.path.join(base_dir, f)
        for f in tracker_files
        if os.path.exists(os.path.join(base_dir, f))
    ]
    with concurrent.futures.ProcessPoolExecutor() as executor:
        future_to_file = {
            executor.submit(extract_domains_from_file, path): path for path in filepaths
        }
        for future in concurrent.futures.as_completed(future_to_file):
            filepath = future_to_file[future]
            try:
                domains = future.result()
                denylist_domains.update(domains)
                print(f"{os.path.basename(filepath)}: {len(domains)} domains")
            except Exception as exc:
                print(f"{os.path.basename(filepath)} generated an exception: {exc}")

    print(f"\nTotal denylist domains: {len(denylist_domains)}")
    return denylist_domains

def process_allowlist_files(base_dir):
    # Extract allowlist domains
    print("\nExtracting allowlist domains...")
    allowlist_domains = set()

    # Control D Bypass
    bypass_file = os.path.join(base_dir, "CD-Control-D-Bypass.json")
    if os.path.exists(bypass_file):
        domains = extract_allowlist_domains_from_file(bypass_file)
        allowlist_domains.update(domains)
        print(f"CD-Control-D-Bypass.json: {len(domains)} domains")

    # Most Abused TLDs (only allowlist entries)
    tlds_file = os.path.join(base_dir, "CD-Most-Abused-TLDs.json")
    if os.path.exists(tlds_file):
        domains = extract_allowlist_domains_from_file(tlds_file)
        allowlist_domains.update(domains)
        print(f"CD-Most-Abused-TLDs.json: {len(domains)} domains")

    print(f"\nTotal allowlist domains: {len(allowlist_domains)}")
    return allowlist_domains

def write_lists(base_dir, denylist_domains, allowlist_domains):
    # Write denylist
    if os.path.exists(base_dir):
        with open(os.path.join(base_dir, "Consolidated-Denylist.txt"), "w") as f:
            if denylist_domains:
                # ⚡ Bolt Optimization: Use join() for faster batched string writing instead of looping f.write()
                f.write("\n".join(sorted(denylist_domains)) + "\n")

        # Write allowlist
        with open(os.path.join(base_dir, "Consolidated-Allowlist.txt"), "w") as f:
            if allowlist_domains:
                # ⚡ Bolt Optimization: Use join() for faster batched string writing instead of looping f.write()
                f.write(
                    "\n".join(f"@@{domain}" for domain in sorted(allowlist_domains))
                    + "\n"
                )

        print(f"\nFiles created:")
        print(f"- Consolidated-Denylist.txt ({len(denylist_domains)} domains)")
        print(f"- Consolidated-Allowlist.txt ({len(allowlist_domains)} domains)")

def main():
    base_dir = os.environ.get("ADGUARD_LISTS_DIR", str(Path.home() / "Downloads"))
    denylist_domains = process_denylist_files(base_dir)
    allowlist_domains = process_allowlist_files(base_dir)
    write_lists(base_dir, denylist_domains, allowlist_domains)

if __name__ == "__main__":
    main()
