import subprocess
import json

def run_gh(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None

ready_prs = [
    "abhimehro/personal-config#744",
    "abhimehro/personal-config#743",
    "abhimehro/personal-config#741",
    "abhimehro/personal-config#740",
    "abhimehro/personal-config#738",
    "abhimehro/personal-config#733",
    "abhimehro/personal-config#732",
    "abhimehro/personal-config#730", # Note: 730 is unstable, check later
    "abhimehro/personal-config#724",
    "abhimehro/ctrld-sync#707",
    "abhimehro/ctrld-sync#706",
    "abhimehro/ctrld-sync#703",
    "abhimehro/ctrld-sync#702",
    "abhimehro/ctrld-sync#700",
    "abhimehro/ctrld-sync#697",
    "abhimehro/email-security-pipeline#642",
    "abhimehro/email-security-pipeline#640",
    "abhimehro/email-security-pipeline#639",
    "abhimehro/email-security-pipeline#632",
    "abhimehro/email-security-pipeline#630",
    "abhimehro/Seatek_Analysis#127",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#108",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#107",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#104",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#102",
]

categorized = {
    'SECURITY': [],
    'DEPENDENCY': [],
    'CI/INFRA': [],
    'PERFORMANCE/REFACTOR/UI/FEATURE': []
}

for pr in ready_prs:
    repo, pr_id = pr.split('#')
    info = run_gh(f"source ../email-security-pipeline/GH_TOKEN.env && gh pr view {pr_id} -R {repo} --json title,mergeStateStatus")
    if not info: continue
    
    # Exclude unstable/dirty
    if info.get('mergeStateStatus') in ['DIRTY', 'CONFLICTING']:
        print(f"Skipping {pr} because it is {info.get('mergeStateStatus')}")
        continue
    
    title = info.get('title', '').lower()
    cat = 'PERFORMANCE/REFACTOR/UI/FEATURE'
    if 'sentinel' in title or 'security' in title or 'cve' in title or 'xxe' in title:
        cat = 'SECURITY'
    elif 'dependabot' in title or 'renovate' in title:
        cat = 'DEPENDENCY'
    elif 'chore' in title or 'ci' in title or 'automation' in title or 'action' in title or 'trunk' in title:
        cat = 'CI/INFRA'
        
    categorized[cat].append((pr, info.get('title')))

for cat, items in categorized.items():
    print(f"\n{cat}:")
    for pr, title in items:
        print(f"  - {pr}: {title}")

