#!/usr/bin/env python3
"""
AdGuard List Consolidation Script

This script consolidates various ad-blocking lists into two comprehensive sets:
1. Denylist - All tracker blocking rules
2. Allowlist - Essential bypass rules and legitimate TLDs

Usage: python3 create_consolidated_lists.py
"""

import json
import os
from pathlib import Path

def extract_domains_from_file(filepath, action_filter=None):
    """Extract domains from a JSON file with optional action filtering."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'rules' in data:
                # ⚡ Bolt Optimization: List comprehension with explicit dictionary checks
                if action_filter is None:
                    return [rule['PK'] for rule in data['rules'] if 'PK' in rule]
                else:
                    return [
                        rule['PK']
                        for rule in data['rules']
                        if 'PK' in rule and 'action' in rule and rule['action'].get('do') == action_filter
                    ]
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return []


def process_allowlist_files(base_dir):
    """Process allowlist files (Control D Bypass + legitimate TLDs)."""
    print("\n📋 Creating Allowlist...")
    allowlist_domains = set()

    # Add Control D Bypass rules (do: 1 = allow)
    bypass_file = base_dir / "CD-Control-D-Bypass.json"
    if bypass_file.exists():
        print("  Processing: CD-Control-D-Bypass.json")
        domains = extract_domains_from_file(bypass_file, action_filter=1)  # Only allow rules
        allowlist_domains.update(domains)
        print(f"    Added {len(domains)} bypass domains")
    else:
        print(f"  ⚠️  File not found: CD-Control-D-Bypass.json")

    # Add legitimate TLDs from Most Abused TLDs (do: 1 = allow)
    tlds_file = base_dir / "CD-Most-Abused-TLDs.json"
    if tlds_file.exists():
        print("  Processing: CD-Most-Abused-TLDs.json")
        domains = extract_domains_from_file(tlds_file, action_filter=1)  # Only allow rules
        allowlist_domains.update(domains)
        print(f"    Added {len(domains)} legitimate TLD domains")
    else:
        print(f"  ⚠️  File not found: CD-Most-Abused-TLDs.json")

    print(f"\n✅ Allowlist total domains: {len(allowlist_domains)}")
    return allowlist_domains

def main():
    # Allow overriding base directory for testing/portability
    base_dir = Path(os.environ.get("ADGUARD_LISTS_DIR", "/Users/abhimehrotra/Downloads"))
    
    print("🔍 Consolidating Ad-Blocking Lists...")
    print("=" * 50)
    
    # 1. CREATE DENYLIST (All tracker blocking rules - do: 0)
    print("\n📋 Creating Denylist...")
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
    
    denylist_domains = set()
    total_tracker_domains = 0
    
    for filename in tracker_files:
        filepath = base_dir / filename
        if filepath.exists():
            print(f"  Processing: {filename}")
            domains = extract_domains_from_file(filepath, action_filter=0)  # Only blocking rules
            denylist_domains.update(domains)
            total_tracker_domains += len(domains)
            print(f"    Added {len(domains)} blocking domains")
        else:
            print(f"  ⚠️  File not found: {filename}")
    
    print(f"\n✅ Denylist total domains: {len(denylist_domains)}")
    
    # 2. CREATE ALLOWLIST (Control D Bypass + legitimate TLDs - do: 1)
    allowlist_domains = process_allowlist_files(base_dir)
    
    # ⚡ Bolt Optimization: Sort once, reuse everywhere (O(N log N))
    sorted_denylist = sorted(denylist_domains)
    sorted_allowlist = sorted(allowlist_domains)

    # 3. CREATE CONSOLIDATED TEXT FILES
    print("\n💾 Creating consolidated text files...")
    
    # Create Denylist text file (one domain per line)
    denylist_txt_path = base_dir / "Consolidated-Denylist.txt"
    with open(denylist_txt_path, 'w', encoding='utf-8') as f:
        f.write("# Consolidated Tracker Denylist for AdGuard macOS\n")
        f.write("# This file contains all domains from various tracker lists that should be blocked\n")
        f.write("# Generated from: Microsoft, No SafeSearch, OPPO/Realme, Roku, Samsung, TikTok, Vivo, Xiaomi, Amazon, Apple, Badware Hoster, LG webOS, Huawei Trackers\n")
        f.write(f"# Total domains: {len(denylist_domains):,}\n\n")
        for domain in sorted_denylist:
            f.write(f"{domain}\n")
    
    # Create Allowlist text file (AdGuard allowlist syntax with @@ prefix)
    allowlist_txt_path = base_dir / "Consolidated-Allowlist.txt"
    with open(allowlist_txt_path, 'w', encoding='utf-8') as f:
        f.write("# Consolidated Allowlist for AdGuard macOS\n")
        f.write("# This file contains domains that should NOT be blocked\n")
        f.write("# Generated from: CD-Control-D-Bypass and legitimate entries from CD-Most-Abused-TLDs\n")
        f.write(f"# Total domains: {len(allowlist_domains):,}\n\n")
        for domain in sorted_allowlist:
            f.write(f"@@{domain}\n")  # AdGuard allowlist syntax
    
    print(f"✅ Created: {denylist_txt_path}")
    print(f"✅ Created: {allowlist_txt_path}")
    
    # 4. CREATE JSON VERSIONS (for reference)
    print("\n💾 Creating JSON reference files...")
    
    # Create Denylist JSON
    denylist_json = {
        "group": {
            "group": "Comprehensive Tracker Denylist",
            "action": {
                "do": 0,
                "status": 1
            }
        },
        "rules": [
            {
                "PK": domain,
                "action": {
                    "do": 0,
                    "status": 1
                }
            }
            for domain in sorted_denylist
        ]
    }
    
    # Create Allowlist JSON
    allowlist_json = {
        "group": {
            "group": "Comprehensive Allowlist",
            "action": {
                "do": 1,
                "status": 1
            }
        },
        "rules": [
            {
                "PK": domain,
                "action": {
                    "do": 1,
                    "status": 1
                }
            }
            for domain in sorted_allowlist
        ]
    }
    
    # Write JSON files
    denylist_json_path = base_dir / "Consolidated-Denylist.json"
    allowlist_json_path = base_dir / "Consolidated-Allowlist.json"
    
    # Use indented JSON for human readability (these are reference files for debugging)
    with open(denylist_json_path, 'w', encoding='utf-8') as f:
        json.dump(denylist_json, f, indent=2, ensure_ascii=False)
    
    with open(allowlist_json_path, 'w', encoding='utf-8') as f:
        json.dump(allowlist_json, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created: {denylist_json_path}")
    print(f"✅ Created: {allowlist_json_path}")
    
    # 5. SUMMARY
    print("\n" + "=" * 50)
    print("🎉 CONSOLIDATION COMPLETE!")
    print("=" * 50)
    print(f"📊 Denylist: {len(denylist_domains):,} domains")
    print(f"📊 Allowlist: {len(allowlist_domains):,} domains")
    print(f"📊 Total processed: {len(denylist_domains) + len(allowlist_domains):,} domains")
    
    print("\n📁 Files created:")
    print(f"  • Consolidated-Denylist.txt (Text format for AdGuard import)")
    print(f"  • Consolidated-Allowlist.txt (Text format for AdGuard import)")
    print(f"  • Consolidated-Denylist.json (JSON reference)")
    print(f"  • Consolidated-Allowlist.json (JSON reference)")
    
    print("\n🚀 Next steps:")
    print("  1. Import Consolidated-Denylist.txt into AdGuard as your denylist")
    print("  2. Import Consolidated-Allowlist.txt into AdGuard as your allowlist")
    print("  3. Test your configuration to ensure proper functionality")
    print("\n📝 Note: AdGuard macOS only supports one denylist and one allowlist.")
    print("    Importing additional lists will override existing ones.")

if __name__ == "__main__":
    main()
