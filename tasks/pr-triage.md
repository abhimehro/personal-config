# PR Triage — 2026-05-14 backlog cleanup (review-and-merge)

**Policy:** Squash merge, stale threshold 30 days. Auto-fix enabled. Strict scrutiny applied to `email-security-pipeline` per Salvage S6 / Lesson 0bb (all mergeable items escalated for infra-fix/salvage).

## In-Scope PR Dispositions

### abhimehro/personal-config

| PR # | Category    | Disposition     | Notes             |
| ---- | ----------- | --------------- | ----------------- |
| 967  | SECURITY    | MERGE           | Canonical         |
| 966  | UI          | MERGE           |                   |
| 965  | CI/INFRA    | MERGE           |                   |
| 964  | CI/INFRA    | MERGE           |                   |
| 963  | CI/INFRA    | MERGE           |                   |
| 962  | PERFORMANCE | MERGE           |                   |
| 960  | SECURITY    | MERGE           |                   |
| 958  | CI/INFRA    | MERGE           |                   |
| 955  | SECURITY    | CLOSE-DUPLICATE | Duplicate of #967 |
| 953  | CI/INFRA    | MERGE           |                   |
| 950  | REFACTOR    | MERGE           |                   |
| 949  | REFACTOR    | MERGE           |                   |
| 948  | REFACTOR    | MERGE           |                   |
| 947  | CI/INFRA    | MERGE           |                   |
| 946  | REFACTOR    | MERGE           |                   |
| 945  | CI/INFRA    | MERGE           |                   |
| 944  | CI/INFRA    | MERGE           |                   |
| 943  | CI/INFRA    | MERGE           |                   |
| 942  | REFACTOR    | MERGE           | Canonical         |
| 940  | SECURITY    | MERGE           |                   |
| 939  | PERFORMANCE | CLOSE-DUPLICATE | Duplicate of #921 |
| 938  | SECURITY    | ESCALATE        | Conflicting       |
| 937  | REFACTOR    | ESCALATE        | Conflicting       |
| 936  | REFACTOR    | MERGE           |                   |
| 935  | PERFORMANCE | MERGE           |                   |
| 934  | SECURITY    | CLOSE-DUPLICATE | Duplicate of #967 |
| 933  | REFACTOR    | CLOSE-DUPLICATE | Duplicate of #942 |
| 932  | PERFORMANCE | MERGE           |                   |
| 930  | SECURITY    | CLOSE-DUPLICATE | Duplicate of #967 |
| 927  | DEPENDENCY  | MERGE           |                   |
| 924  | PERFORMANCE | MERGE           |                   |
| 923  | SECURITY    | CLOSE-DUPLICATE | Duplicate of #967 |
| 921  | PERFORMANCE | MERGE           | Canonical         |

### abhimehro/ctrld-sync

| PR # | Category    | Disposition     | Notes             |
| ---- | ----------- | --------------- | ----------------- |
| 810  | SECURITY    | MERGE           | Canonical         |
| 809  | UI          | MERGE           | Canonical         |
| 808  | REFACTOR    | MERGE           | Canonical         |
| 806  | REFACTOR    | MERGE           | Canonical         |
| 805  | REFACTOR    | MERGE           |                   |
| 804  | REFACTOR    | MERGE           |                   |
| 803  | REFACTOR    | CLOSE-DUPLICATE | Duplicate of #808 |
| 802  | REFACTOR    | CLOSE-DUPLICATE | Duplicate of #806 |
| 800  | REFACTOR    | MERGE           |                   |
| 798  | REFACTOR    | MERGE           |                   |
| 795  | REFACTOR    | MERGE           |                   |
| 794  | REFACTOR    | MERGE           |                   |
| 793  | REFACTOR    | MERGE           |                   |
| 792  | REFACTOR    | MERGE           |                   |
| 791  | REFACTOR    | MERGE           | Canonical         |
| 790  | REFACTOR    | CLOSE-DUPLICATE | Duplicate of #808 |
| 789  | UI          | CLOSE-DUPLICATE | Duplicate of #809 |
| 788  | PERFORMANCE | MERGE           | Canonical         |
| 787  | SECURITY    | CLOSE-DUPLICATE | Duplicate of #810 |
| 784  | PERFORMANCE | CLOSE-DUPLICATE | Duplicate of #788 |
| 783  | SECURITY    | CLOSE-DUPLICATE | Duplicate of #810 |
| 782  | UI          | MERGE           |                   |
| 781  | REFACTOR    | CLOSE-DUPLICATE | Duplicate of #791 |
| 780  | SECURITY    | MERGE           |                   |
| 778  | REFACTOR    | CLOSE-DUPLICATE | Duplicate of #791 |

### abhimehro/email-security-pipeline

_Note: Strict scrutiny applied. Pipeline has pre-existing test infra breakage (Lesson 0t/0bb) or security-classified status requiring all salvage/merges to be drafted or escalated._
| PR # | Category | Disposition | Notes |
|---|---|---|---|
| 850 | UI | ESCALATE | Canonical |
| 849 | UI | CLOSE-DUPLICATE | Duplicate of #850 |
| 848 | CI/INFRA | ESCALATE | Canonical |
| 845 | CI/INFRA | ESCALATE | |
| 844 | REFACTOR | ESCALATE | |
| 842 | PERFORMANCE | ESCALATE | |
| 841 | PERFORMANCE | ESCALATE | Canonical |
| 840 | CI/INFRA | ESCALATE | |
| 839 | CI/INFRA | ESCALATE | |
| 838 | REFACTOR | ESCALATE | |
| 835 | CI/INFRA | ESCALATE | |
| 834 | PERFORMANCE | CLOSE-DUPLICATE | Duplicate of #841 |
| 833 | REFACTOR | ESCALATE | Canonical |
| 832 | REFACTOR | ESCALATE | Canonical |
| 830 | CI/INFRA | CLOSE-DUPLICATE | Duplicate of #848 |
| 825 | REFACTOR | ESCALATE | Canonical |
| 824 | REFACTOR | ESCALATE | Canonical |
| 819 | CI/INFRA | ESCALATE | |
| 818 | CI/INFRA | ESCALATE | |
| 817 | REFACTOR | ESCALATE | |
| 816 | PERFORMANCE | ESCALATE | Conflicting |
| 815 | UI | ESCALATE | Canonical |
| 814 | UI | CLOSE-DUPLICATE | Duplicate of #815 |
| 811 | CI/INFRA | ESCALATE | Canonical |
| 809 | CI/INFRA | CLOSE-DUPLICATE | Duplicate of #811 |
| 807 | PERFORMANCE | ESCALATE | |
| 806 | UI | CLOSE-DUPLICATE | Duplicate of #815 |
| 805 | UI | CLOSE-DUPLICATE | Duplicate of #815 |

### abhimehro/Seatek_Analysis

| PR # | Category    | Disposition     | Notes             |
| ---- | ----------- | --------------- | ----------------- |
| 183  | SECURITY    | MERGE           |                   |
| 182  | SECURITY    | MERGE           |                   |
| 181  | PERFORMANCE | MERGE           |                   |
| 180  | REFACTOR    | MERGE           |                   |
| 178  | PERFORMANCE | MERGE           |                   |
| 177  | REFACTOR    | MERGE           |                   |
| 176  | PERFORMANCE | MERGE           |                   |
| 175  | REFACTOR    | MERGE           |                   |
| 174  | PERFORMANCE | MERGE           |                   |
| 172  | REFACTOR    | MERGE           |                   |
| 171  | PERFORMANCE | MERGE           | Canonical         |
| 170  | PERFORMANCE | CLOSE-DUPLICATE | Duplicate of #171 |
| 169  | PERFORMANCE | CLOSE-DUPLICATE | Duplicate of #171 |
| 168  | DEPENDENCY  | MERGE           |                   |
| 167  | PERFORMANCE | MERGE           |                   |

### abhimehro/Hydrograph_Versus_Seatek_Sensors_Project

| PR # | Category    | Disposition | Notes |
| ---- | ----------- | ----------- | ----- |
| 177  | PERFORMANCE | MERGE       |       |

### abhimehro/series_correction_project_updated

| PR # | Category    | Disposition     | Notes            |
| ---- | ----------- | --------------- | ---------------- |
| 33   | PERFORMANCE | MERGE           | Canonical        |
| 26   | REFACTOR    | MERGE           |                  |
| 25   | PERFORMANCE | ESCALATE        | Conflicting      |
| 24   | PERFORMANCE | CLOSE-DUPLICATE | Duplicate of #33 |
| 23   | PERFORMANCE | MERGE           | Canonical        |
| 22   | SECURITY    | MERGE           |                  |
| 21   | PERFORMANCE | CLOSE-DUPLICATE | Duplicate of #23 |
| 20   | PERFORMANCE | CLOSE-DUPLICATE | Duplicate of #23 |
| 19   | REFACTOR    | MERGE           |                  |
| 18   | PERFORMANCE | CLOSE-DUPLICATE | Duplicate of #23 |
| 17   | PERFORMANCE | CLOSE-DUPLICATE | Duplicate of #23 |

## Archive — 2026-05-09 run

**Policy:** Squash merge, stale threshold 30 days (no qualifying **stale closures** this run — queue skews under 7 days old), auto-fix enabled (no branch pushes this pass; no safe auto-fix opportunities taken).

### SUPERSEDED

- abhimehro/Seatek_Analysis#162 — superseded by **#164** (CRITICAL OOM fix on same `Updated_Seatek_Analysis.R` path); closed after **#164** merged.

### DUPLICATE

- abhimehro/email-security-pipeline#786 — duplicate of **#785** (identical `caching.py` / test / journal delta); **#785** merged first, **#786** closed.

### STALE (>30d, no activity)

- _(none in-scope at snapshot; re-evaluate on next run with `updatedAt` vs `stale_threshold_days`.)_

### CONFLICTING / DEFER (human rebase; no force-push)

- abhimehro/series_correction_project_updated#13, #14 — conflicts after **#12** squash-merge (Lesson 0cc cascade).
- abhimehro/ctrld-sync#771 — conflicts after **#773** merge (same pluralization lane).
- abhimehro/Seatek_Analysis#163 — **UNSTABLE** CI at snapshot; not merged.

### READY (merged this session — cross-check `main`)

- abhimehro/dotfiles#907, #904
- abhimehro/email-security-pipeline#785
- abhimehro/series_correction_project_updated#12
- abhimehro/Seatek_Analysis#164, #161
- abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#172
- abhimehro/ctrld-sync#773

### ESCALATE / trust boundary (commented; not merged)

- abhimehro/dotfiles#893 — `summary.yml` / LLM output → shell trust boundary (re-tagged in session comment).
- abhimehro/ctrld-sync#769 — Devin branch: shell injection hardening in automation summary path.
- abhimehro/ctrld-sync#775 — Sentinel authorization / log leakage class (overlaps **#772**, **#774**, **#770**; needs human dedup).

### ZERO-DIFF CLOSED (no merge; Lesson 0b)

- abhimehro/dotfiles#908
- abhimehro/email-security-pipeline#788, #782

### REMAINING HIGH-VOLUME (dotfiles repo)

Large overlapping Bolt/Jules/Sentinel queues (**#901** `CONFLICTING`, **#910**–**#903**, etc.): prefer **one semantic lane** at a time; re-fetch `mergeable` after each merge (Lesson 0cc).

## Planned mutations (executed / superseded)

### abhimehro/personal-config

```bash
# Merges
gh pr merge 967 --repo abhimehro/personal-config --squash
gh pr merge 966 --repo abhimehro/personal-config --squash
gh pr merge 965 --repo abhimehro/personal-config --squash
gh pr merge 964 --repo abhimehro/personal-config --squash
gh pr merge 963 --repo abhimehro/personal-config --squash
gh pr merge 962 --repo abhimehro/personal-config --squash
gh pr merge 960 --repo abhimehro/personal-config --squash
gh pr merge 958 --repo abhimehro/personal-config --squash
gh pr merge 953 --repo abhimehro/personal-config --squash
gh pr merge 950 --repo abhimehro/personal-config --squash
gh pr merge 949 --repo abhimehro/personal-config --squash
gh pr merge 948 --repo abhimehro/personal-config --squash
gh pr merge 947 --repo abhimehro/personal-config --squash
gh pr merge 946 --repo abhimehro/personal-config --squash
gh pr merge 945 --repo abhimehro/personal-config --squash
gh pr merge 944 --repo abhimehro/personal-config --squash
gh pr merge 943 --repo abhimehro/personal-config --squash
gh pr merge 942 --repo abhimehro/personal-config --squash
gh pr merge 940 --repo abhimehro/personal-config --squash
gh pr merge 936 --repo abhimehro/personal-config --squash
gh pr merge 935 --repo abhimehro/personal-config --squash
gh pr merge 932 --repo abhimehro/personal-config --squash
gh pr merge 927 --repo abhimehro/personal-config --squash
gh pr merge 924 --repo abhimehro/personal-config --squash
gh pr merge 921 --repo abhimehro/personal-config --squash

# Closes
gh pr close 955 --repo abhimehro/personal-config --comment 'Duplicate of #967'
gh pr close 939 --repo abhimehro/personal-config --comment 'Duplicate of #921'
gh pr close 934 --repo abhimehro/personal-config --comment 'Duplicate of #967'
gh pr close 933 --repo abhimehro/personal-config --comment 'Duplicate of #942'
gh pr close 930 --repo abhimehro/personal-config --comment 'Duplicate of #967'
gh pr close 923 --repo abhimehro/personal-config --comment 'Duplicate of #967'
```

### abhimehro/ctrld-sync

```bash
# Merges
gh pr merge 810 --repo abhimehro/ctrld-sync --squash
gh pr merge 809 --repo abhimehro/ctrld-sync --squash
gh pr merge 808 --repo abhimehro/ctrld-sync --squash
gh pr merge 806 --repo abhimehro/ctrld-sync --squash
gh pr merge 805 --repo abhimehro/ctrld-sync --squash
gh pr merge 804 --repo abhimehro/ctrld-sync --squash
gh pr merge 800 --repo abhimehro/ctrld-sync --squash
gh pr merge 798 --repo abhimehro/ctrld-sync --squash
gh pr merge 795 --repo abhimehro/ctrld-sync --squash
gh pr merge 794 --repo abhimehro/ctrld-sync --squash
gh pr merge 793 --repo abhimehro/ctrld-sync --squash
gh pr merge 792 --repo abhimehro/ctrld-sync --squash
gh pr merge 791 --repo abhimehro/ctrld-sync --squash
gh pr merge 788 --repo abhimehro/ctrld-sync --squash
gh pr merge 782 --repo abhimehro/ctrld-sync --squash
gh pr merge 780 --repo abhimehro/ctrld-sync --squash

# Closes
gh pr close 803 --repo abhimehro/ctrld-sync --comment 'Duplicate of #808'
gh pr close 802 --repo abhimehro/ctrld-sync --comment 'Duplicate of #806'
gh pr close 790 --repo abhimehro/ctrld-sync --comment 'Duplicate of #808'
gh pr close 789 --repo abhimehro/ctrld-sync --comment 'Duplicate of #809'
gh pr close 787 --repo abhimehro/ctrld-sync --comment 'Duplicate of #810'
gh pr close 784 --repo abhimehro/ctrld-sync --comment 'Duplicate of #788'
gh pr close 783 --repo abhimehro/ctrld-sync --comment 'Duplicate of #810'
gh pr close 781 --repo abhimehro/ctrld-sync --comment 'Duplicate of #791'
gh pr close 778 --repo abhimehro/ctrld-sync --comment 'Duplicate of #791'
```

### abhimehro/email-security-pipeline

```bash
# Closes
gh pr close 849 --repo abhimehro/email-security-pipeline --comment 'Duplicate of #850'
gh pr close 834 --repo abhimehro/email-security-pipeline --comment 'Duplicate of #841'
gh pr close 830 --repo abhimehro/email-security-pipeline --comment 'Duplicate of #848'
gh pr close 814 --repo abhimehro/email-security-pipeline --comment 'Duplicate of #815'
gh pr close 809 --repo abhimehro/email-security-pipeline --comment 'Duplicate of #811'
gh pr close 806 --repo abhimehro/email-security-pipeline --comment 'Duplicate of #815'
gh pr close 805 --repo abhimehro/email-security-pipeline --comment 'Duplicate of #815'
```

### abhimehro/Seatek_Analysis

```bash
# Merges
gh pr merge 183 --repo abhimehro/Seatek_Analysis --squash
gh pr merge 182 --repo abhimehro/Seatek_Analysis --squash
gh pr merge 181 --repo abhimehro/Seatek_Analysis --squash
gh pr merge 180 --repo abhimehro/Seatek_Analysis --squash
gh pr merge 178 --repo abhimehro/Seatek_Analysis --squash
gh pr merge 177 --repo abhimehro/Seatek_Analysis --squash
gh pr merge 176 --repo abhimehro/Seatek_Analysis --squash
gh pr merge 175 --repo abhimehro/Seatek_Analysis --squash
gh pr merge 174 --repo abhimehro/Seatek_Analysis --squash
gh pr merge 172 --repo abhimehro/Seatek_Analysis --squash
gh pr merge 171 --repo abhimehro/Seatek_Analysis --squash
gh pr merge 168 --repo abhimehro/Seatek_Analysis --squash
gh pr merge 167 --repo abhimehro/Seatek_Analysis --squash

# Closes
gh pr close 170 --repo abhimehro/Seatek_Analysis --comment 'Duplicate of #171'
gh pr close 169 --repo abhimehro/Seatek_Analysis --comment 'Duplicate of #171'
```

### abhimehro/Hydrograph_Versus_Seatek_Sensors_Project

```bash
# Merges
gh pr merge 177 --repo abhimehro/Hydrograph_Versus_Seatek_Sensors_Project --squash
```

### abhimehro/series_correction_project_updated

```bash
# Merges
gh pr merge 33 --repo abhimehro/series_correction_project_updated --squash
gh pr merge 26 --repo abhimehro/series_correction_project_updated --squash
gh pr merge 23 --repo abhimehro/series_correction_project_updated --squash
gh pr merge 22 --repo abhimehro/series_correction_project_updated --squash
gh pr merge 19 --repo abhimehro/series_correction_project_updated --squash

# Closes
gh pr close 24 --repo abhimehro/series_correction_project_updated --comment 'Duplicate of #33'
gh pr close 21 --repo abhimehro/series_correction_project_updated --comment 'Duplicate of #23'
gh pr close 20 --repo abhimehro/series_correction_project_updated --comment 'Duplicate of #23'
gh pr close 18 --repo abhimehro/series_correction_project_updated --comment 'Duplicate of #23'
gh pr close 17 --repo abhimehro/series_correction_project_updated --comment 'Duplicate of #23'
```
