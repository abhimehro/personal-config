import json
import os
from pathlib import Path
import concurrent.futures


def _process_tracker_file_for_extract(base_dir, filename):
    filepath = os.path.join(base_dir, filename)
    if os.path.exists(filepath):
        domains = extract_domains_from_file(filepath)
        print(f"{filename}: {len(domains)} domains")
        return set(domains)
    return set()


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


if __name__ == "__main__":
    # Base directory
    base_dir = os.environ.get("ADGUARD_LISTS_DIR", str(Path.home() / "Downloads"))

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

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(_process_tracker_file_for_extract, base_dir, filename): filename for filename in tracker_files}
        for future in concurrent.futures.as_completed(futures):
            try:
                domains = future.result()
                denylist_domains.update(domains)
            except Exception as exc:
                filename = futures[future]
                print(f"{filename} generated an exception: {exc}")

    print(f"\nTotal denylist domains: {len(denylist_domains)}")

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
