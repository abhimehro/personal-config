#!/usr/bin/env python3
import subprocess
import os
from collections import defaultdict

pr_info = {
    169: ("adguard-scripts-fix-12771850971742957063", "security: remove hardcoded paths in adguard"),
    172: ("sentinel/fix-sed-portability-891822583618688263", "security: fix sed portability"),
    175: ("sentinel-fix-credentials-leak-4573352824312365028", "security: fix credentials in media server"),
    178: ("sentinel-media-server-binding-13293653919583392074", "security: fix 0.0.0.0 binding"),
    181: ("sentinel-fix-credentials-9881772433040572380", "security: fix credentials + hardcoded paths"),
    182: ("bolt/optimize-controld-manager-status-check-5638893552934211644", "perf: optimize controld status"),
    185: ("bolt-optimize-startup-polling-16024478546999091251", "perf: optimize startup polling"),
    188: ("bolt/shell-optimization-3950176997351290456", "perf: shell parameter expansion"),
    194: ("bolt/optimize-verify-script-9885104625875968774", "perf: optimize verify script"),
    170: ("bolt/parallel-verify-10381006191754613467", "perf: parallelize verify"),
    173: ("bolt-optimize-health-check-11533376331034950860", "perf: health check optimization"),
    195: ("palette-windscribe-connect-ux-4427475041254526425", "UX: windscribe connect"),
    192: ("palette/network-mode-indicators-13134460049874570757", "UX: active state indicators"),
    189: ("palette-cli-ux-polish-12244564018616630218", "UX: maintenance CLI polish"),
    186: ("palette-interactive-maintenance-15223838811589577227", "UX: interactive dashboard"),
    174: ("palette-youtube-downloader-ux-improvements-5499888140330439457", "UX: youtube downloader"),
    171: ("palette-verify-ssh-ux-8987400674580001920", "UX: SSH verify"),
    168: ("palette-ssh-install-ux-350175493376774504", "UX: SSH install"),
    166: ("palette-ssh-config-ux-7779700014438421465", "UX: SSH install - DUPLICATE of 168"),
}

# Build file change map
file_changes = defaultdict(lambda: defaultdict(list))  # file -> pr -> changes

for pr_num in sorted(pr_info.keys()):
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", "main", f"pr-{pr_num}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                parts = line.split(None, 1)
                if len(parts) == 2:
                    status, filepath = parts
                    file_changes[filepath][pr_num].append(status)
    except Exception as e:
        print(f"Error processing PR {pr_num}: {e}")

# Print analysis
print("=" * 80)
print("FILE CHANGE ANALYSIS BY PR")
print("=" * 80)
print()

# Group files by type
core_files = defaultdict(list)
for filepath, prs in sorted(file_changes.items()):
    # Skip boilerplate files that are in ALL PRs
    if filepath in ['.Jules/palette.md', '.gitignore', 'README.md']:
        continue
    if '.github/' in filepath or '.jest' in filepath:
        continue
    if filepath.startswith('.'):
        continue
    if 'fish_history' in filepath or 'copilot-instructions' in filepath:
        continue
    
    # Categorize
    if 'adguard' in filepath:
        category = 'ADGUARD'
    elif 'sentinel' in filepath or 'security' in filepath:
        category = 'SENTINEL/SECURITY'
    elif 'controld' in filepath or 'controld-system' in filepath:
        category = 'CONTROLD'
    elif 'maintenance' in filepath or 'health_check' in filepath:
        category = 'MAINTENANCE/HEALTH'
    elif 'scripts/' in filepath or 'network-mode' in filepath or 'windscribe' in filepath or 'setup-controld' in filepath:
        category = 'BOLT SCRIPTS'
    else:
        category = 'OTHER'
    
    core_files[category].append((filepath, prs))

for category in sorted(core_files.keys()):
    print(f"\n{'='*80}")
    print(f"CATEGORY: {category}")
    print('='*80)
    for filepath, prs_dict in sorted(core_files[category]):
        pr_list = sorted(prs_dict.keys())
        statuses = {pr: prs_dict[pr][0] for pr in pr_list}
        print(f"\n  {filepath}")
        print(f"    Changed by PRs: {', '.join([f'#{pr}' for pr in pr_list])}")
        for pr in sorted(pr_list):
            branch_name, desc = pr_info[pr]
            print(f"      #{pr}: {desc}")

# Find conflicts and duplicates
print("\n\n" + "=" * 80)
print("POTENTIAL CONFLICTS & DUPLICATES")
print("=" * 80)

conflicts = defaultdict(list)
for filepath, prs_dict in file_changes.items():
    if filepath in ['.Jules/palette.md', '.gitignore', 'README.md', '.github/copilot-instructions.md']:
        continue
    if 'fish_history' in filepath:
        continue
    if len(prs_dict) > 1:
        pr_list = sorted(prs_dict.keys())
        conflicts[filepath] = pr_list

print("\nFILES CHANGED BY MULTIPLE PRs (Potential Conflicts):")
for filepath in sorted(conflicts.keys()):
    pr_list = conflicts[filepath]
    print(f"\n  {filepath}")
    print(f"    Affected PRs: {', '.join([f'#{pr}' for pr in pr_list])}")
    for pr in pr_list:
        branch_name, desc = pr_info[pr]
        print(f"      #{pr}: {desc}")

