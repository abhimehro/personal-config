#!/usr/bin/env python3
"""
AdGuard List Consolidation Script

This script consolidates various ad-blocking lists into two comprehensive sets:
1. Denylist - All tracker blocking rules
2. Allowlist - Essential bypass rules and legitimate TLDs

Usage: python3 consolidate_adblock_lists.py --input-dir <input_dir> --output-dir <output_dir>
"""

import json
import os
import argparse
import sys
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
    # ⚡ Bolt Optimization: Use list comprehension for faster domain extraction
    return [rule['PK'] for rule in rules if 'PK' in rule]

def process_tracker_files(base_dir, tracker_files):
    """Process tracker files to create denylist domains."""
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
    return denylist_domains

def extract_allowlist_from_file(filepath, description):
    """Extract allowlist domains from a file with do: 1 rules."""
    domains = set()
    if filepath.exists():
        print(f"  Processing: {filepath.name}")
        data = load_json_file(filepath)
        if data and 'rules' in data:
            # ⚡ Bolt Optimization: Use generator expression with `in` checks instead of nested `.get()`
            domains.update(
                rule['PK']
                for rule in data['rules']
                if 'PK' in rule and 'action' in rule and rule['action'].get('do') == 1
            )
            count = len(domains)
            print(f"    Added {count} {description}")
    return domains

def process_allowlist_files(base_dir):
    """Process allowlist files (Control D Bypass + legitimate TLDs)."""
    print("\n📋 Creating Allowlist...")
    allowlist_domains = set()
    
    # Add Control D Bypass rules
    bypass_file = base_dir / "CD-Control-D-Bypass.json"
    allowlist_domains.update(extract_allowlist_from_file(bypass_file, "bypass domains"))
    
    # Add legitimate TLDs
    tlds_file = base_dir / "CD-Most-Abused-TLDs.json"
    allowlist_domains.update(extract_allowlist_from_file(tlds_file, "legitimate TLD domains"))
    
    print(f"\n✅ Allowlist total domains: {len(allowlist_domains)}")
    return allowlist_domains

def create_json_structure(domains, group_name, action_do):
    """Create JSON structure for domain lists."""
    return {
        "group": {
            "group": group_name,
            "action": {
                "do": action_do,
                "status": 1
            }
        },
        "rules": [
            {
                "PK": domain,
                "action": {
                    "do": action_do,
                    "status": 1
                }
            }
            for domain in sorted(domains)
        ]
    }

def write_json_files(output_dir, denylist_domains, allowlist_domains):
    """Write JSON formatted list files."""
    print("\n💾 Creating consolidated files...")
    
    denylist_json = create_json_structure(denylist_domains, "Comprehensive Tracker Denylist", 0)
    allowlist_json = create_json_structure(allowlist_domains, "Comprehensive Allowlist", 1)
    
    denylist_path = output_dir / "Consolidated-Denylist.json"
    allowlist_path = output_dir / "Consolidated-Allowlist.json"
    
    with open(denylist_path, 'w', encoding='utf-8') as f:
        json.dump(denylist_json, f, indent=2, ensure_ascii=False)
    
    with open(allowlist_path, 'w', encoding='utf-8') as f:
        json.dump(allowlist_json, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created: {denylist_path}")
    print(f"✅ Created: {allowlist_path}")
    return denylist_path, allowlist_path

def write_text_files(output_dir, denylist_domains, allowlist_domains):
    """Write text formatted list files for AdGuard."""
    print("\n📄 Creating simple text versions for AdGuard...")
    
    denylist_txt_path = output_dir / "Consolidated-Denylist.txt"
    with open(denylist_txt_path, 'w', encoding='utf-8') as f:
        for domain in sorted(denylist_domains):
            f.write(f"{domain}\n")
    
    allowlist_txt_path = output_dir / "Consolidated-Allowlist.txt"
    with open(allowlist_txt_path, 'w', encoding='utf-8') as f:
        for domain in sorted(allowlist_domains):
            f.write(f"@@{domain}\n")
    
    print(f"✅ Created: {denylist_txt_path}")
    print(f"✅ Created: {allowlist_txt_path}")
    return denylist_txt_path, allowlist_txt_path

def print_summary(denylist_domains, allowlist_domains, output_dir):
    """Print consolidation summary."""
    print("\n" + "=" * 50)
    print("🎉 CONSOLIDATION COMPLETE!")
    print("=" * 50)
    print(f"📊 Denylist: {len(denylist_domains):,} domains")
    print(f"📊 Allowlist: {len(allowlist_domains):,} domains")
    print(f"📊 Total processed: {len(denylist_domains) + len(allowlist_domains):,} domains")
    
    print("\n📁 Files created in {}:".format(output_dir))
    print(f"  • Consolidated-Denylist.json (JSON format)")
    print(f"  • Consolidated-Allowlist.json (JSON format)")
    print(f"  • Consolidated-Denylist.txt (Text format)")
    print(f"  • Consolidated-Allowlist.txt (Text format)")
    
    print("\n🚀 Next steps:")
    print("  1. Import Consolidated-Denylist.txt into AdGuard as your denylist")
    print("  2. Import Consolidated-Allowlist.txt into AdGuard as your allowlist")
    print("  3. Test your configuration to ensure proper functionality")

def main():
    """Main consolidation workflow."""
    parser = argparse.ArgumentParser(description="Consolidate AdGuard blocklists.")
    parser.add_argument("--input-dir", type=Path, default=Path("."), help="Directory containing input JSON files (default: current directory)")
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="Directory to write output files (default: current directory)")

    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: Input directory '{input_dir}' does not exist or is not a directory.")
        sys.exit(1)

    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error: Could not create output directory '{output_dir}': {e}")
            sys.exit(1)
    
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
    
    print("🔍 Consolidating Ad-Blocking Lists...")
    print(f"Input Directory: {input_dir}")
    print(f"Output Directory: {output_dir}")
    print("=" * 50)
    
    # Process files
    denylist_domains = process_tracker_files(input_dir, tracker_files)
    allowlist_domains = process_allowlist_files(input_dir)
    
    # Write output files
    write_json_files(output_dir, denylist_domains, allowlist_domains)
    write_text_files(output_dir, denylist_domains, allowlist_domains)
    
    # Print summary
    print_summary(denylist_domains, allowlist_domains, output_dir)

if __name__ == "__main__":
    main()
