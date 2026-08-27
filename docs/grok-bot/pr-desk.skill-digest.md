# Skill + routine (only after the first digest is good)

## Save as a skill

Ask PR Desk:

```text
Save the process we just used as a skill called “PR Desk weekday digest.”
Include: live sources, the Output block, max five human items, stale-data
rule, and that GitHub writes / Cloud Agent launches / ledger CAS always
require my explicit approval in this thread. Do not create a routine yet.
```

A useful skill states when to use it, inputs, sequence, validation, return
format, and what needs approval
([skills](https://docs.x.ai/grok-bot/skills-routines-and-automations)).

## Sequence the skill should capture

1. Fetch the runtime ledger. If it cannot be read, stop with `SOURCE_MISSING`.
2. Count open PRs and MERGEABLE non-draft BOT PRs across the seven repos.
3. Read today’s `pr-lifecycle-docs-YYYYMMDD` head if open; else yesterday’s
   lineage if still open; else skip docs (do not invent a run).
4. Compare open-PR count to the previous digest in this thread.
5. Flag pipeline stalls only: unused Stage 1 product slots + rising open PRs,
   SHA_MATCH skip of executable work, Stage 3 calibration still enabled,
   empty Stage 2 theater, both Stage 3 variants enabled.
6. Collect at most five `WAITING_HUMAN` / irreducible `REVIEW_SECURITY` items
   that already have a packet or a one-sentence question. Skip overlap clusters.
7. Post the Output block in this conversation. Do not post to Slack/GitHub.

## Then create the routine

Timezone: America/Chicago. Stage 3 fires at 19:00 UTC. This digest waits until
evening so Abhi can review after class.

```text
Every weekday at 8:00 PM America/Chicago, run the PR Desk weekday digest
skill. Post the Output block in this conversation only. Do not send Slack or
email. Do not touch GitHub. If the runtime ledger or GitHub is unavailable,
report SOURCE_MISSING instead of reusing an old digest. If I have not opened
the last three digests, skip and say you paused.
```

Use **Test run** once on a weekday after 19:00 UTC. A test run does real work
([routines](https://docs.x.ai/grok-bot/skills-routines-and-automations)); keep
writes behind approval.

Do not add a GitHub-notification routine in v1.
