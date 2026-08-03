# gh-stack Quick Reference

A one-page command cheat sheet for working with stacked pull requests using the
`github/gh-stack` `gh` extension. For the full workflow and the reasoning behind
it, see the `Stacked PRs during review/salvage sessions` section in
[`AGENTS.md`](../../AGENTS.md) and the skill at
`.agents/skills/gh-stack/SKILL.md`.

## Creating a stack

```bash
# From existing open PRs (same repo, overlapping files), bottom to top
gh stack link <pr-bottom> <pr-middle> <pr-top>

# From new branches (chained from the start)
gh stack init <branch-a> <branch-b> <branch-c>
\`\`\`

## Day-to-day commands

| Command | What it does |
| ------- | ------------ |
| `gh stack view` | Show the current stack, each layer, and its PR |
| \`gh stack rebase --no-trunk\` | Rebase every layer onto the one below (run before submit/merge) |
| \`gh stack submit --auto\` | Push branches and open/update the stack of PRs |
| \`gh stack push\` | Push branch updates without opening new PRs |
| \`gh stack merge --yes\` | Merge the whole stack (top-down) after review |

## The golden rules

1. **Rebase before you submit or merge.** \`gh stack init\` creates branches off
   trunk in parallel; the first \`gh stack rebase --no-trunk\` is what actually
   chains them.
2. **Never merge stacked PRs with \`gh pr merge\` or auto-merge.** They are
   rejected with "part of a stack… use the asynchronous merge REST API".
3. **Merge only the top of the stack.** Merging the top folds every lower layer
   into the ultimate base.
4. **Merging requires a human.** Review/Salvage agents may \`link\`/\`init\` and
   open drafts, but never run \`gh stack merge\` unattended (boundary S1).

See [`docs/automated-pr-review-agent.md`](../automated-pr-review-agent.md) (and the linked `AGENTS.md` section) for what to do when a stack goes `DIRTY` or a layer is
accidentally merged out of order.
```
