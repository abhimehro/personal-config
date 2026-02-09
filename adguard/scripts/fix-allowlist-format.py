#!/usr/bin/env python3
"""
Fix Allowlist Format for AdGuard

This script converts the allowlist from filter rule format (@@domain.com) 
to AdGuard allowlist format (plain domain names).

Usage: python3 fix-allowlist-format.py
"""

import json
import os
from pathlib import Path

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

def main():
    base_dir = Path.home() / "Downloads"
    
    print("🔧 Fixing Allowlist Format for AdGuard")
    print("=" * 50)
    
    allowlist_domains = set()
    
    # Add Control D Bypass rules (do: 1 = allow)
    bypass_file = base_dir / "CD-Control-D-Bypass.json"
    if bypass_file.exists():
        print("📋 Processing: CD-Control-D-Bypass.json")
        domains = extract_allowlist_domains_from_file(bypass_file)
        allowlist_domains.update(domains)
        print(f"   Added {len(domains)} bypass domains")
    else:
        print("⚠️  CD-Control-D-Bypass.json not found")
    
    # Add legitimate TLDs from Most Abused TLDs (do: 1 = allow)
    tlds_file = base_dir / "CD-Most-Abused-TLDs.json"
    if tlds_file.exists():
        print("📋 Processing: CD-Most-Abused-TLDs.json")
        domains = extract_allowlist_domains_from_file(tlds_file)
        allowlist_domains.update(domains)
        print(f"   Added {len(domains)} legitimate TLD domains")
    else:
        print("⚠️  CD-Most-Abused-TLDs.json not found")
    
    print(f"\n✅ Total unique allowlist domains: {len(allowlist_domains)}")
    
    # Create the corrected allowlist file
    allowlist_path = base_dir / "Consolidated-Allowlist-Fixed.txt"
    with open(allowlist_path, 'w', encoding='utf-8') as f:
        f.write("# Consolidated Allowlist for AdGuard macOS\n")
        f.write("# This file contains domains that should NOT be blocked\n")
        f.write("# Generated from: CD-Control-D-Bypass and legitimate entries from CD-Most-Abused-TLDs\n")
        f.write(f"# Total domains: {len(allowlist_domains):,}\n\n")
        
        for domain in sorted(allowlist_domains):
            f.write(f"{domain}\n")
    
    print(f"✅ Created: {allowlist_path}")
    print(f"📊 File contains {len(allowlist_domains):,} domains")
    
    print("\n🔧 FORMAT FIXED!")
    print("=" * 50)
    print("❌ Old format: @@domain.com (filter rule format)")
    print("✅ New format: domain.com (allowlist format)")
    
    print(f"\n🚀 Next steps:")
    print(f"  1. Delete the old allowlist from AdGuard")
    print(f"  2. Import Consolidated-Allowlist-Fixed.txt")
    print(f"  3. Verify all domains are accepted")

if __name__ == "__main__":
    main()
