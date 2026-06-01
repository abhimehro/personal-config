# PR Triage — 2026-06-01

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · DEFER · CLOSE-SUPERSEDED · CLOSE-DUPLICATE · ESCALATE

## Duplicate & overlap analysis

| Group | Keeper (merged) | Closed as duplicate | Rationale |
| --- | --- | --- | --- |
| pc `final-media-server.sh` eval | **#1141** | #1131, #1120 | Same file; newest Sentinel fix |
| pc `windscribe-connect.sh` | **#1130** | #1123, #1118 | Trap restoration overlap |
| pc `smart_scheduler` / `performance_optimizer` | Partial via #1140 batch | #1138, #1137, #1129, #1128 | Conflicts after merges; **#1139** deferred |
| esp Daily QA / tarfile zero-diff | **#1005** merged | **#1002** closed | Zero-diff on `main` |
| esp Bolt email parsing | **#1000** | #998 | Same paths |
| esp app_runner permission tests | **#1003** open | #1001, #997 | Keeper blocked on checks |
| esp media error tests | **#995** | #991, #987, #981, #980 | Same test file |
| esp resize tests | **#986** merged | #979 | Same test module |
| esp IMAP tests | **#984** deferred | #974 closed | #984 CONFLICTING post-merge |

## Session dispositions (executed)

| Disposition | Count | Repos |
| --- | ---: | --- |
| **MERGE** | 38 | pc, esp, Seatek |
| **CLOSE-DUPLICATE / SUPERSEDED** | 20 | pc, esp |
| **DEFER** | 12 | pc, esp, Seatek, series |
| **ESCALATE** | 4 | pc (#1132, #1125), esp (#973), Seatek (#238) |

## Security notes

| PR | Tier | Assessment |
| --- | --- | --- |
| pc #1141–#1107 batch | SECURITY | Eval-injection hardening merged where CI green and mergeable |
| pc #1132, #1125 | Trust boundary | `run_merges.py` — human review required |
| esp #1004 | SECURITY | TOCTOU file permissions — merged |
| esp #999 | SECURITY | Zip Slip — CodeScene failing; defer |
| esp #973 | SECURITY | NLP eval FP — conflicting; escalate |
| Seatek #235 | SECURITY | CRITICAL TOCTOU — merged |
| Seatek #238 | SECURITY/PERF | Failing required CI — escalate |

## CI anomalies

| PR | Check | Action |
| --- | --- | --- |
| esp #999 | CodeScene fail | DEFER (no merge with failing check) |
| esp #1003 | checks fail | DEFER |
| Seatek #238 | lint-and-test, validate | ESCALATE — verify `main` |
| series #90 | CodeScene fail | DEFER |
| pc #1132, #1125 | CONFLICTING | ESCALATE + salvage |

## Merge order (executed)

1. Zero-diff QA (esp #1005)  
2. Security TOCTOU (esp #1004, Seatek #235)  
3. personal-config eval-injection keepers (unique files first)  
4. Code health / test PRs (non-conflicting)  
5. Close duplicates and conflicting superseded siblings

## Post-session remainder (Salvage input)

```yaml
- repo: abhimehro/personal-config
  pr: 1139
  reason: CONFLICTING smart_scheduler eval fix after security merge batch
- repo: abhimehro/personal-config
  pr: 1113
  reason: CONFLICTING rotate-media-webdav false-positive eval cleanup
- repo: abhimehro/personal-config
  pr: 1132
  reason: ESCALATE run_merges.py parallelization
- repo: abhimehro/personal-config
  pr: 1125
  reason: ESCALATE run_merges.py loop parallelization
- repo: abhimehro/email-security-pipeline
  pr: 999
  reason: CodeScene fail + CONFLICTING tarfile Zip Slip
- repo: abhimehro/Seatek_Analysis
  pr: 238
  reason: Required CI failing on main-side validate/lint
- repo: abhimehro/Seatek_Analysis
  pr: 237
  reason: CONFLICTING after #235 merge
- repo: abhimehro/series_correction_project_updated
  pr: 90
  reason: CodeScene fail on perf vectorization
```
