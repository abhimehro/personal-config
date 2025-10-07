import json
import os

def extract_domains_from_file(filepath):
    """Extract domains from a JSON file."""
    domains = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'rules' in data:
                for rule in data['rules']:
                    if 'PK' in rule:
                        domains.append(rule['PK'])
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return domains

def extract_allowlist_domains_from_file(filepath):
    """Extract allowlist domains (do: 1) from a JSON file."""
    domains = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'rules' in data:
                for rule in data['rules']:
                    if 'PK' in rule and rule.get('action', {}).get('do') == 1:
                        domains.append(rule['PK'])
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return domains

# Base directory
base_dir = "/Users/abhimehrotra/Downloads"

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
    "CD-Huawei-Tracker.json"
]

print("Extracting denylist domains...")
denylist_domains = set()

for filename in tracker_files:
    filepath = os.path.join(base_dir, filename)
    if os.path.exists(filepath):
        domains = extract_domains_from_file(filepath)
        denylist_domains.update(domains)
        print(f"{filename}: {len(domains)} domains")

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
with open(os.path.join(base_dir, "Consolidated-Denylist.txt"), 'w') as f:
    for domain in sorted(denylist_domains):
        f.write(f"{domain}\n")

# Write allowlist
with open(os.path.join(base_dir, "Consolidated-Allowlist.txt"), 'w') as f:
    for domain in sorted(allowlist_domains):
        f.write(f"@@{domain}\n")

print(f"\nFiles created:")
print(f"- Consolidated-Denylist.txt ({len(denylist_domains)} domains)")
print(f"- Consolidated-Allowlist.txt ({len(allowlist_domains)} domains)")
