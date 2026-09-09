# PR lifecycle drain retro - 2026-09-03

## Outcome

Grok Bot HITL three-stage pipeline (PR Desk + Stage 1/2/3) drained open PRs
across the seven configured repos from ~154 to 68 (CAS ledger revision 55).
Cursor daily Automations stayed paused during the drain; weeklies may remain on
for gap-fill. Stage 3 calibration remains disabled; completion remains the live
Stage 3 variant (APPROVED 7/7).

## What unblocked drain

- Dense Stage 1 Dependabot patch/minor clusters (5-6 merges/session).
- Sibling Dependabot update-branch after earlier merge in the same batch.
- Docs-only HOLD_PLATFORM exception (Swift/make) for templates/docs BOT PRs.
- Explicit GHAS infra-miss ignore when no real finding.
- Desk-named REVIEW_SECURITY / HUMAN salvage exceptions (e.g. Seatek #801).
- personal-config TRUNK_QUEUE discipline.
- Caps 80 inventory / 40 product mutations with salvage work items as
  bookkeeping (not product mutations).

## What still sticks

| Class                            | Examples                                                       | Owner                    |
| -------------------------------- | -------------------------------------------------------------- | ------------------------ |
| Workflow consolidate             | pc #2142, email #1527                                          | human / Stage 3 packet   |
| Major deps                       | ai-inference 2-3, upload-sarif 3-4, OpenCV 5, pandas 3, mypy 2 | human                    |
| REVIEW_SECURITY salvage          | ctrld #1195                                                    | Desk exception or packet |
| Open Notion packets              | Hydro #543 vs #535; Seatek #708                                | human                    |
| Mega CI_INFRA                    | Seatek #643 venv deletion                                      | new gitignore-only draft |
| HUMAN Palette/Bolt/Sentinel pile | many personal-config MERGABLE under abhimehro                  | not Stage 1 BOT routine  |

## Stage 2 queue (process before 2026-09-07T05:20:00Z)

- s2-20260831-series-390-spreadsheet-safety
- s2-20260831-email-1512-nlp-aho
- s2-20260831-ctrld-1207-prng-jitter

## Resume checklist (Cursor Dashboard)

- Paste updated `docs/cursor-automations/prompts/daily-pr-review.md` into Stage
  1 `77c168e0-7f6b-42de-bad6-da4e4e640b79` (no enablement toggle required if
  already set).
- Paste `daily-pr-salvage.md` into Stage 2
  `3e537981-04a6-456f-89a3-272d9d5fddd7`.
- Paste `daily-pr-completion.md` into Stage 3 completion
  `66a8e7a8-9c42-11f1-ba66-0e7d0216e441`.
- Leave calibration `d9d2c058-9c42-11f1-ba66-0e7d0216e441` disabled.
- Re-enable Stage 1 -> Stage 2 -> Stage 3 completion only after paste plus a
  usage reassessment.
- Record new dashboard fingerprints on the next ledger event.

## Prompt source of truth

Updated paste bodies live in this change under
`docs/cursor-automations/prompts/`. Spec docs (`automated-pr-*-agent.md`) remain
normative; prompt files are Dashboard paste records plus the 2026-09-03 addenda.
