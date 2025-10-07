#!/usr/bin/env python3
"""
AdGuard List Consolidation Script

This script consolidates various ad-blocking lists into two comprehensive sets:
1. Denylist - All tracker blocking rules
2. Allowlist - Essential bypass rules and legitimate TLDs

Usage: python3 consolidate_adblock_lists.py
"""

import json
import os
from pathlib import Path

def load_json_file(filepath):
    """Load and parse a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def extract_domains_from_rules(rules):
    """Extract domain names from rules array."""
    domains = []
    for rule in rules:
        if 'PK' in rule:
            domains.append(rule['PK'])
    return domains

def main():
    # Define the base directory
    base_dir = Path("/Users/abhimehrotra/Downloads")
    
    # Define tracker files for denylist (all should block with do: 0)
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
        "CD-Huawei-Tracker.json"  # Adding this as it's also a tracker
    ]
    
    print("🔍 Consolidating Ad-Blocking Lists...")
    print("=" * 50)
    
    # 1. CREATE DENYLIST (All tracker blocking rules)
    print("\n📋 Creating Denylist...")
    denylist_domains = set()
    
    for filename in tracker_files:
        filepath = base_dir / filename
        if filepath.exists():
            print(f"  Processing: {filename}")
            data = load_json_file(filepath)
            if data and 'rules' in data:
                domains = extract_domains_from_rules(data['rules'])
                denylist_domains.update(domains)
                print(f"    Added {len(domains)} domains")
        else:
            print(f"  ⚠️  File not found: {filename}")
    
    print(f"\n✅ Denylist total domains: {len(denylist_domains)}")
    
    # 2. CREATE ALLOWLIST (Control D Bypass + legitimate TLDs)
    print("\n📋 Creating Allowlist...")
    allowlist_domains = set()
    
    # Add Control D Bypass rules (do: 1 = allow)
    bypass_file = base_dir / "CD-Control-D-Bypass.json"
    if bypass_file.exists():
        print("  Processing: CD-Control-D-Bypass.json")
        data = load_json_file(bypass_file)
        if data and 'rules' in data:
            # Only include rules with do: 1 (allow)
            for rule in data['rules']:
                if 'PK' in rule and rule.get('action', {}).get('do') == 1:
                    allowlist_domains.add(rule['PK'])
            print(f"    Added {len([r for r in data['rules'] if r.get('action', {}).get('do') == 1])} bypass domains")
    
    # Add legitimate TLDs from Most Abused TLDs (do: 1 = allow)
    tlds_file = base_dir / "CD-Most-Abused-TLDs.json"
    if tlds_file.exists():
        print("  Processing: CD-Most-Abused-TLDs.json")
        data = load_json_file(tlds_file)
        if data and 'rules' in data:
            # Only include rules with do: 1 (allow legitimate domains)
            for rule in data['rules']:
                if 'PK' in rule and rule.get('action', {}).get('do') == 1:
                    allowlist_domains.add(rule['PK'])
            print(f"    Added {len([r for r in data['rules'] if r.get('action', {}).get('do') == 1])} legitimate TLD domains")
    
    print(f"\n✅ Allowlist total domains: {len(allowlist_domains)}")
    
    # 3. CREATE CONSOLIDATED FILES
    print("\n💾 Creating consolidated files...")
    
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
            for domain in sorted(denylist_domains)
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
            for domain in sorted(allowlist_domains)
        ]
    }
    
    # Write files
    denylist_path = base_dir / "Consolidated-Denylist.json"
    allowlist_path = base_dir / "Consolidated-Allowlist.json"
    
    with open(denylist_path, 'w', encoding='utf-8') as f:
        json.dump(denylist_json, f, indent=2, ensure_ascii=False)
    
    with open(allowlist_path, 'w', encoding='utf-8') as f:
        json.dump(allowlist_json, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created: {denylist_path}")
    print(f"✅ Created: {allowlist_path}")
    
    # 4. CREATE SIMPLE TEXT VERSIONS (for AdGuard import)
    print("\n📄 Creating simple text versions for AdGuard...")
    
    # Denylist text file (one domain per line)
    denylist_txt_path = base_dir / "Consolidated-Denylist.txt"
    with open(denylist_txt_path, 'w', encoding='utf-8') as f:
        for domain in sorted(denylist_domains):
            f.write(f"{domain}\n")
    
    # Allowlist text file (one domain per line)
    allowlist_txt_path = base_dir / "Consolidated-Allowlist.txt"
    with open(allowlist_txt_path, 'w', encoding='utf-8') as f:
        for domain in sorted(allowlist_domains):
            f.write(f"@@{domain}\n")  # AdGuard allowlist syntax
    
    print(f"✅ Created: {denylist_txt_path}")
    print(f"✅ Created: {allowlist_txt_path}")
    
    # 5. SUMMARY
    print("\n" + "=" * 50)
    print("🎉 CONSOLIDATION COMPLETE!")
    print("=" * 50)
    print(f"📊 Denylist: {len(denylist_domains):,} domains")
    print(f"📊 Allowlist: {len(allowlist_domains):,} domains")
    print(f"📊 Total processed: {len(denylist_domains) + len(allowlist_domains):,} domains")
    
    print("\n📁 Files created:")
    print(f"  • Consolidated-Denylist.json (JSON format)")
    print(f"  • Consolidated-Allowlist.json (JSON format)")
    print(f"  • Consolidated-Denylist.txt (Text format)")
    print(f"  • Consolidated-Allowlist.txt (Text format)")
    
    print("\n🚀 Next steps:")
    print("  1. Import Consolidated-Denylist.txt into AdGuard as your denylist")
    print("  2. Import Consolidated-Allowlist.txt into AdGuard as your allowlist")
    print("  3. Test your configuration to ensure proper functionality")

if __name__ == "__main__":
    main()
