#!/usr/bin/env python3
import subprocess
import json
import sys

# PR numbers and their expected branch names
prs = {
    169: "adguard-scripts-fix-12771850971742957063",
    172: "sentinel/fix-sed-portability-891822583618688263", 
    175: "sentinel-fix-credentials-leak-4573352824312365028",
    178: "sentinel-media-server-binding-13293653919583392074",
    181: "sentinel-fix-credentials-9881772433040572380",
    182: "bolt/optimize-controld-manager-status-check-5638893552934211644",
    185: "bolt-optimize-startup-polling-16024478546999091251",
    188: "bolt/shell-optimization-3950176997351290456",
    194: "bolt/optimize-verify-script-9885104625875968774",
    170: "bolt/parallel-verify-10381006191754613467",
    173: "bolt-optimize-health-check-11533376331034950860",
    195: "palette-windscribe-connect-ux-4427475041254526425",
    192: "palette/network-mode-indicators-13134460049874570757",
    189: "palette-cli-ux-polish-12244564018616630218",
    186: "palette-interactive-maintenance-15223838811589577227",
    174: "palette-youtube-downloader-ux-improvements-5499888140330439457",
    171: "palette-verify-ssh-ux-8987400674580001920",
    168: "palette-ssh-install-ux-350175493376774504",
    166: "palette-ssh-config-ux-7779700014438421465",
}

# Try to get PR info from GitHub API
for pr_num, branch_name in prs.items():
    try:
        # Use GitHub CLI if available
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_num), "--json", "files,title,body"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pr_data = json.loads(result.stdout)
            print(f"\n{'='*60}")
            print(f"PR #{pr_num}: {pr_data.get('title', 'N/A')}")
            print(f"{'='*60}")
            if "files" in pr_data and pr_data["files"]:
                for file in pr_data["files"]:
                    print(f"  {file.get('path', 'unknown')}")
            else:
                print("  (No files or unable to fetch)")
        else:
            print(f"PR #{pr_num}: GitHub CLI not available or PR not found")
    except Exception as e:
        print(f"PR #{pr_num}: Error - {e}")

