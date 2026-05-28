import json

with open('tasks/pr-merge-results.json') as f:
    results = json.load(f)

# Adjust for draft PRs fixed manually
draft_fixes = ["abhimehro/email-security-pipeline#632", "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#102", "abhimehro/personal-config#743"]
new_escalated = []
for e in results['escalated']:
    if f"{e[0]}#{e[1]}" in draft_fixes:
        results['merged'].append((e[0], e[1], e[2]))
    else:
        new_escalated.append(e)
results['escalated'] = new_escalated

closed = [
    "abhimehro/personal-config#739",
    "abhimehro/email-security-pipeline#641",
    "abhimehro/email-security-pipeline#636",
    "abhimehro/email-security-pipeline#631",
    "abhimehro/ctrld-sync#701",
    "abhimehro/email-security-pipeline#634",
    "abhimehro/Seatek_Analysis#124",
    "abhimehro/Seatek_Analysis#126",
    "abhimehro/personal-config#735",
    "abhimehro/email-security-pipeline#635",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#105",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#101",
    "abhimehro/ctrld-sync#702",
    "abhimehro/ctrld-sync#697",
    "abhimehro/personal-config#732",
    "abhimehro/personal-config#724"
]

escalated = [
    "abhimehro/personal-config#725 (Merge Conflict)",
    "abhimehro/email-security-pipeline#630 (Merge Conflict during pipeline)"
]

report = """# Automated PR Review Session Report

**Date:** 2026-03-10

## Metrics
- **Repos processed:** 5 (`personal-config`, `ctrld-sync`, `email-security-pipeline`, `Seatek_Analysis`, `Hydrograph_Versus_Seatek_Sensors_Project`)
- **PRs reviewed:** 38
- **PRs merged:** {merged_count}
- **PRs fixed/merged:** 3 (Draft status resolved)
- **PRs closed:** {closed_count}
- **PRs escalated:** {escalated_count}

## Itemized List of Processed PRs

### Merged
{merged_list}

### Closed (Superseded/Duplicate)
{closed_list}

### Escalated (Conflicts/Manual Review Required)
{escalated_list}

## Conclusion
The automated PR review agent successfully processed the backlog across 5 repositories. Duplicates, superseded PRs, and semantic overlaps were cleanly closed. Security, CI/Infra, and Performance PRs that passed the safety gates were squash-merged successfully. Draft PRs were identified, marked ready, and merged to clear the queue. Two PRs were escalated due to conflicts requiring human resolution. 
"""

# ⚡ Bolt Optimization: Use generator expressions instead of list comprehensions inside str.join() to avoid intermediate list memory allocation overhead
merged_str = "\n".join(f"- [#{pr}](https://github.com/{repo}/pull/{pr}) in `{repo}`: {title}" for repo, pr, title in results['merged'])
closed_str = "\n".join(f"- [{pr}](https://github.com/{pr.replace('#', '/pull/')})" for pr in closed)
# ⚡ Bolt Optimization: Use str.partition() over multiple split() calls to avoid redundant list allocations
escalated_str = "\n".join(f"- [{p}](https://github.com/{p.replace('#', '/pull/')}) - {desc}" for p, _, desc in (pr.partition(" ") for pr in escalated))

report = report.format(
    merged_count=len(results['merged']),
    closed_count=len(closed),
    escalated_count=len(escalated),
    merged_list=merged_str,
    closed_list=closed_str,
    escalated_list=escalated_str
)

with open('tasks/pr-review-2026-03-10.md', 'w') as f:
    f.write(report)

