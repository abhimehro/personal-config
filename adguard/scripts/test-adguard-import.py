#!/usr/bin/env python3
"""
AdGuard Import Verification Script

This script helps verify that your consolidated lists are properly formatted
and ready for AdGuard import.

Usage: python3 test-adguard-import.py
"""

import os
from pathlib import Path

def verify_file_format(filepath, file_type):
    """Verify that a file is properly formatted for AdGuard import."""
    issues = []
    
    if not os.path.exists(filepath):
        return [f"❌ File not found: {filepath}"]
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        comment_lines = 0
        empty_lines = 0
        valid_domains = 0
        invalid_lines = 0
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            if not line:  # Empty line
                empty_lines += 1
            elif line.startswith('#'):  # Comment line
                comment_lines += 1
            elif file_type == 'denylist':
                # Denylist: just domain names
                if '.' in line and not line.startswith('@@'):
                    valid_domains += 1
                else:
                    invalid_lines += 1
                    issues.append(f"Line {i}: Invalid domain format - '{line}'")
            elif file_type == 'allowlist':
                # Allowlist: domains with @@ prefix
                if line.startswith('@@') and '.' in line[2:]:
                    valid_domains += 1
                else:
                    invalid_lines += 1
                    issues.append(f"Line {i}: Invalid allowlist format - '{line}'")
        
        # Summary
        print(f"\n📊 {file_type.upper()} ANALYSIS:")
        print(f"  Total lines: {total_lines:,}")
        print(f"  Comment lines: {comment_lines:,}")
        print(f"  Empty lines: {empty_lines:,}")
        print(f"  Valid domains: {valid_domains:,}")
        print(f"  Invalid lines: {invalid_lines:,}")
        
        if invalid_lines > 0:
            print(f"  ⚠️  Issues found: {len(issues)}")
            for issue in issues[:5]:  # Show first 5 issues
                print(f"    {issue}")
            if len(issues) > 5:
                print(f"    ... and {len(issues) - 5} more issues")
        else:
            print(f"  ✅ All lines are properly formatted!")
        
        return issues
        
    except Exception as e:
        return [f"❌ Error reading file: {e}"]

def check_file_encoding(filepath):
    """Check if file is properly UTF-8 encoded."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read()
        return True, "✅ UTF-8 encoding verified"
    except UnicodeDecodeError:
        return False, "❌ UTF-8 encoding issue detected"
    except Exception as e:
        return False, f"❌ Encoding check failed: {e}"

def main():
    base_dir = Path("/Users/abhimehrotra/Downloads")
    
    print("🔍 AdGuard Import Verification")
    print("=" * 50)
    
    # Check denylist
    denylist_path = base_dir / "Consolidated-Denylist.txt"
    print(f"\n📋 Checking Denylist: {denylist_path.name}")
    
    encoding_ok, encoding_msg = check_file_encoding(denylist_path)
    print(f"  {encoding_msg}")
    
    denylist_issues = verify_file_format(denylist_path, 'denylist')
    
    # Check allowlist
    allowlist_path = base_dir / "Consolidated-Allowlist.txt"
    print(f"\n📋 Checking Allowlist: {allowlist_path.name}")
    
    encoding_ok, encoding_msg = check_file_encoding(allowlist_path)
    print(f"  {encoding_msg}")
    
    allowlist_issues = verify_file_format(allowlist_path, 'allowlist')
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 IMPORT READINESS SUMMARY")
    print("=" * 50)
    
    denylist_ready = len(denylist_issues) == 0
    allowlist_ready = len(allowlist_issues) == 0
    
    if denylist_ready and allowlist_ready:
        print("🎉 ALL FILES READY FOR IMPORT!")
        print("\n✅ Your consolidated lists are properly formatted and ready to import into AdGuard.")
        print("\n📋 Next steps:")
        print("  1. Follow the AdGuard-Import-Guide.md instructions")
        print("  2. Import Consolidated-Denylist.txt as a custom filter")
        print("  3. Import Consolidated-Allowlist.txt in the Allowlist section")
        print("  4. Test your configuration")
    else:
        print("⚠️  ISSUES DETECTED - REVIEW BEFORE IMPORT")
        print("\n❌ Some files have formatting issues that should be fixed before importing.")
        print("\n🔧 Recommended actions:")
        if not denylist_ready:
            print("  - Fix issues in Consolidated-Denylist.txt")
        if not allowlist_ready:
            print("  - Fix issues in Consolidated-Allowlist.txt")
        print("  - Re-run this verification script")
        print("  - Consider using the Python consolidation scripts for complete lists")
    
    print(f"\n📁 Files checked:")
    print(f"  • {denylist_path.name} - {'✅ Ready' if denylist_ready else '❌ Issues'}")
    print(f"  • {allowlist_path.name} - {'✅ Ready' if allowlist_ready else '❌ Issues'}")

if __name__ == "__main__":
    main()
