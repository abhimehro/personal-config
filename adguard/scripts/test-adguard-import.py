#!/usr/bin/env python3
"""
AdGuard Import Verification Script

This script helps verify that your consolidated lists are properly formatted
and ready for AdGuard import.

Usage: python3 test-adguard-import.py
"""

import os
from pathlib import Path


def validate_line(line, line_num, file_type):
    """Validate a single line based on file type.

    Returns: (is_valid, issue_message)
    """
    line = line.strip()

    if not line:  # Empty line
        return True, None
    elif line.startswith("#"):  # Comment line
        return True, None
    elif file_type == "denylist":
        # Denylist: just domain names
        if "." in line and not line.startswith("@@"):
            return True, None
        else:
            return False, f"Line {line_num}: Invalid domain format - '{line}'"
    elif file_type == "allowlist":
        # Allowlist: domains with @@ prefix
        if line.startswith("@@") and "." in line[2:]:
            return True, None
        else:
            return False, f"Line {line_num}: Invalid allowlist format - '{line}'"

    return False, f"Line {line_num}: Unknown format - '{line}'"


def count_line_types(lines, file_type):
    """Count and categorize lines, collecting validation issues."""
    stats = {"total": len(lines), "comments": 0, "empty": 0, "valid": 0, "invalid": 0}
    issues = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped:
            stats["empty"] += 1
        elif stripped.startswith("#"):
            stats["comments"] += 1
        else:
            is_valid, issue_msg = validate_line(line, i, file_type)
            if is_valid:
                stats["valid"] += 1
            else:
                stats["invalid"] += 1
                issues.append(issue_msg)

    return stats, issues


def print_file_analysis(file_type, stats, issues):
    """Print analysis results for a file."""
    print(f"\n📊 {file_type.upper()} ANALYSIS:")
    print(f"  Total lines: {stats['total']:,}")
    print(f"  Comment lines: {stats['comments']:,}")
    print(f"  Empty lines: {stats['empty']:,}")
    print(f"  Valid domains: {stats['valid']:,}")
    print(f"  Invalid lines: {stats['invalid']:,}")

    if stats["invalid"] > 0:
        print(f"  ⚠️  Issues found: {len(issues)}")
        for issue in issues[:5]:  # Show first 5 issues
            print(f"    {issue}")
        if len(issues) > 5:
            print(f"    ... and {len(issues) - 5} more issues")
    else:
        print(f"  ✅ All lines are properly formatted!")


def verify_file_format(filepath, file_type):
    """Verify that a file is properly formatted for AdGuard import."""
    if not os.path.exists(filepath):
        return [f"❌ File not found: {filepath}"]

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        stats, issues = count_line_types(lines, file_type)
        print_file_analysis(file_type, stats, issues)

        return issues

    except Exception as e:
        return [f"❌ Error reading file: {e}"]


def check_file_encoding(filepath):
    """Check if file is properly UTF-8 encoded."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
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

    denylist_issues = verify_file_format(denylist_path, "denylist")

    # Check allowlist
    allowlist_path = base_dir / "Consolidated-Allowlist.txt"
    print(f"\n📋 Checking Allowlist: {allowlist_path.name}")

    encoding_ok, encoding_msg = check_file_encoding(allowlist_path)
    print(f"  {encoding_msg}")

    allowlist_issues = verify_file_format(allowlist_path, "allowlist")

    # Summary
    print("\n" + "=" * 50)
    print("📊 IMPORT READINESS SUMMARY")
    print("=" * 50)

    denylist_ready = len(denylist_issues) == 0
    allowlist_ready = len(allowlist_issues) == 0

    if denylist_ready and allowlist_ready:
        print("🎉 ALL FILES READY FOR IMPORT!")
        print(
            "\n✅ Your consolidated lists are properly formatted and ready to import into AdGuard."
        )
        print("\n📋 Next steps:")
        print("  1. Follow the AdGuard-Import-Guide.md instructions")
        print("  2. Import Consolidated-Denylist.txt as a custom filter")
        print("  3. Import Consolidated-Allowlist.txt in the Allowlist section")
        print("  4. Test your configuration")
    else:
        print("⚠️  ISSUES DETECTED - REVIEW BEFORE IMPORT")
        print(
            "\n❌ Some files have formatting issues that should be fixed before importing."
        )
        print("\n🔧 Recommended actions:")
        if not denylist_ready:
            print("  - Fix issues in Consolidated-Denylist.txt")
        if not allowlist_ready:
            print("  - Fix issues in Consolidated-Allowlist.txt")
        print("  - Re-run this verification script")
        print("  - Consider using the Python consolidation scripts for complete lists")

    print(f"\n📁 Files checked:")
    print(f"  • {denylist_path.name} - {'✅ Ready' if denylist_ready else '❌ Issues'}")
    print(
        f"  • {allowlist_path.name} - {'✅ Ready' if allowlist_ready else '❌ Issues'}"
    )


if __name__ == "__main__":
    main()
