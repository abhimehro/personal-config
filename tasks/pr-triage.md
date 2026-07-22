# PR Triage — 2026-07-21 (Phase 2 Salvage)

**Preflight:** PASS 7/7 · **Mode:** salvage (draft-only) · **Remainder in:** 23

## Salvage clusters

| Keep (draft) | Close originals | Reason |
|--------------|-----------------|--------|
| pc [#1734](https://github.com/abhimehro/personal-config/pull/1734) | #1716 #1717 #1723 | Automation-task tests; drop `pr-visual-recap.yml` smuggling |
| pc [#1735](https://github.com/abhimehro/personal-config/pull/1735) | #1726 | `run_shell_command` tests + junk submit stub deletes |
| pc [#1736](https://github.com/abhimehro/personal-config/pull/1736) | #1718 | `run_workflow_updater` helper extraction |
| esp [#1334](https://github.com/abhimehro/email-security-pipeline/pull/1334) | #1331 | IMAP size-parse list-comp; append-only bolt.md |
| esp [#1335](https://github.com/abhimehro/email-security-pipeline/pull/1335) | #1314 | ingestion `extend`+comprehension; append-only bolt.md |

## Close-superseded (docs)

| PR | Reason |
|----|--------|
| pc #1706 | Prior Phase 2 docs conflicted; replaced by this session |

## Auto-resolved (next Phase 1)

| PR | Reason |
|----|--------|
| pc #1724 | MERGEABLE/CLEAN + CodeScene green |
| esp #1320 | MERGEABLE/CLEAN |

## Escalate (leave open)

| PR | Reason |
|----|--------|
| pc #1721 | `lru_cache` on GH token env loader |
| esp #1328 | TOCTOU/chmod config secrets |
| esp #1324 | Auth-Results scoring |
| esp #1319 | `gh_token_cli` token writes |
| sc #275/#276/#268 | `dummy_todos.py` auth/PBKDF2/DoS (Lesson 0ef) |
| rpce #126/#127 | tip-release artifact majors (Lesson 0dw) |

## Defer (CodeScene)

| PR | Reason |
|----|--------|
| esp #1327 | `/cs-agent` already posted; still pending |
| esp #1330/#1311 | `/cs-agent` posted this run; await remediation |

## Dropped

| PR | Reason |
|----|--------|
| hg #374 | MERGED since Phase 1 |
