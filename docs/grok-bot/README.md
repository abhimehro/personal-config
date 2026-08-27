# Grok Bot — PR Desk (human filter)

Grok Bot is useful here as a **chief-of-staff filter**, not as a fourth PR
pipeline. Cursor Automations already own review, salvage, and completion.
Another executor would compete with Stage 1/3, burn a second usage meter, and
add more write-ups to read.

The pain this Bot is allowed to solve: a solo maintainer cannot absorb
`tasks/*-session-reports.md`, lessons, and Stage 3 packets at class-start
volume. The Bot compresses that into **at most five human decisions** and a
throughput line.

Official role analog: [Chief of Staff](https://docs.x.ai/grok-bot/use-cases) on
[Grok Bot](https://docs.x.ai/grok-bot/overview). Grok Bot is a persistent
teammate with its own computer
([overview](https://docs.x.ai/grok-bot/overview)); it is **not** a Cursor Cloud
Agent run and **not** a Dashboard Automation.

## Architecture

| Layer                   | Owns                                           | Must not                                           |
| ----------------------- | ---------------------------------------------- | -------------------------------------------------- |
| Stage 1/2/3 Automations | Merge/close/draft/CAS ledger                   | Human inbox, extra docs PRs                        |
| Runtime ledger          | Current owner of every PR                      | Being rewritten from Grok Bot                      |
| Notion packets          | Irreducible Stage 3 questions                  | Session-report dumps                               |
| **Grok Bot PR Desk**    | Digest, stall flags, one recommended next step | GitHub mutations, Cloud Agent launches, new issues |

```text
15:00 Stage 1  →  17:00 Stage 2  →  19:00 Stage 3
                                          ↓
                         01:00 UTC  PR Desk digest (8:00 PM CDT)
                                          ↓
                         Abhi: ≤5 decisions, or "nothing for you"
```

## Setup (about fifteen minutes)

1. Sign into the Grok Bot app with the **same Cursor account** that owns the
   Automations ([sign-in](https://cursor.com/help/grok-bot/sign-in)).
2. **New → Create new agent**. Profile:
   [pr-desk.profile.md](pr-desk.profile.md).
3. Plugins: GitHub (read) and Notion if offered. Skip Gmail, Calendar, Slack,
   and X for v1. Cursor GitHub App (Automations) is a **separate** connection
   from a Grok Bot GitHub plugin
   ([skills/routines](https://docs.x.ai/grok-bot/skills-routines-and-automations)).
4. Run the first task from [pr-desk.first-task.md](pr-desk.first-task.md).
   Correct the digest once.
5. Save the method as a skill from
   [pr-desk.skill-digest.md](pr-desk.skill-digest.md), then a **weekday**
   routine at `01:00` UTC (8:00 PM CDT). Output stays in the Bot thread.
6. Notifications on. Do **not** subscribe to every GitHub notification.

Promotion path matches the product
([use cases](https://docs.x.ai/grok-bot/use-cases)): description → one real task
→ correct → skill → second input → routine. Keep external writes behind approval
([approvals](https://docs.x.ai/grok-bot/approvals-security-and-privacy)).

## What “assign work” means

Do not file GitHub issues (that is how the backlog grew). Do not launch Cursor
Cloud Agents (that duplicates Automations and spends a second meter).

Assigning work here means: name the existing owner (Stage 1, Stage 2, you), cite
the ledger `next_action`, and if a one-off Cloud Agent is truly needed,
**draft** the prompt in-thread and wait for approval.

## Cost and failure modes

- Grok Bot usage is a **weekly Cursor-account meter**, separate from Automations
  ([plans](https://cursor.com/help/grok-bot/plans)). A broad event listener will
  burn it.
- Grok Bot requires cloud storage; Legacy Privacy Mode is unsupported
  ([FAQ](https://docs.x.ai/grok-bot/faq)).
- Bots share one computer; they are not a security boundary
  ([overview](https://docs.x.ai/grok-bot/overview)).
- Routines may pause after a long absence
  ([routines](https://docs.x.ai/grok-bot/skills-routines-and-automations)).
- If the digest is longer than one screen, the Bot failed. Tighten the skill; do
  not add a second Bot.

## Later (only if v1 stays short)

- A 15:30 UTC stall check: “Did Stage 1 use product-mutation slots?”
- Slack DM of the same five-item digest, still no GitHub writes.
- Teaching a 10-minute browser walkthrough of “read ledger → five decisions”
  ([teach a task](https://docs.x.ai/grok-bot/skills-routines-and-automations)).
