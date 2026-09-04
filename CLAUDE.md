<!-- gitnexus:start -->

# GitNexus — Code Intelligence

This project is indexed by GitNexus as **personal-config** (8429 symbols, 11258
relationships, 286 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the
> project root — it auto-selects an available runner. No `.gitnexus/run.cjs`
> yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g.
> `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact analysis before editing.** Use
  `impact({target: "symbolName", direction: "upstream"})` (MCP) or
  `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .`
  (CLI fallback); report callers, processes, and risk. Never substitute grep for
  graph analysis.
- **MUST analyze graph changes before committing.** Use
  `detect_changes({scope: "all"})` (MCP) or
  `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback).
  `partial: true` or `truncated: true` is not a clean check — a zero means
  unseen, not unaffected; re-run it. For regression review:
  `detect_changes({scope: "compare", base_ref: "main"})` or
  `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before
  proceeding with edits.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set
  is not evidence the symbol is unused — it can also mean the callers are not
  resolvable by the index (plain-object property access, dynamic dispatch,
  cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so.
  Confirm with a text search before treating the symbol as safe to change or
  delete; do not proceed on the strength of a zero.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find
  execution flows instead of grepping. It returns process-grouped results ranked
  by relevance.
- When you need full context on a specific symbol — callers, callees, which
  execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings
  (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never
  read `UNKNOWN` as an all-clear — it means the walk could not answer, which is
  the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands
  the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource                                         | Use for                                  |
| ------------------------------------------------ | ---------------------------------------- |
| `gitnexus://repo/personal-config/context`        | Codebase overview, check index freshness |
| `gitnexus://repo/personal-config/clusters`       | All functional areas                     |
| `gitnexus://repo/personal-config/processes`      | All execution flows                      |
| `gitnexus://repo/personal-config/process/{name}` | Step-by-step execution trace             |

## CLI

| Task                                         | Read this skill file                                  |
| -------------------------------------------- | ----------------------------------------------------- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md`          |
| Blast radius / "What breaks if I change X?"  | `.claude/skills/gitnexus-impact-analysis/SKILL.md`    |
| Trace bugs / "Why is X failing?"             | `.claude/skills/gitnexus-debugging/SKILL.md`          |
| Rename / extract / split / refactor          | `.claude/skills/gitnexus-refactoring/SKILL.md`        |
| Tools, resources, schema reference           | `.claude/skills/gitnexus-guide/SKILL.md`              |
| Index, status, clean, wiki CLI commands      | `.claude/skills/gitnexus-cli/SKILL.md`                |
| Work in the Tests area (451 symbols)         | `.claude/skills/gitnexus-area-tests/SKILL.md`         |
| Work in the Scripts area (230 symbols)       | `.claude/skills/gitnexus-area-scripts/SKILL.md`       |
| Work in the Morning-brief area (64 symbols)  | `.claude/skills/gitnexus-area-morning-brief/SKILL.md` |
| Work in the Benchmarks area (14 symbols)     | `.claude/skills/gitnexus-area-benchmarks/SKILL.md`    |
| Work in the Copilot-demo area (8 symbols)    | `.claude/skills/gitnexus-area-copilot-demo/SKILL.md`  |
| Work in the Cluster_32 area (6 symbols)      | `.claude/skills/gitnexus-area-cluster-32/SKILL.md`    |
| Work in the Cluster_35 area (6 symbols)      | `.claude/skills/gitnexus-area-cluster-35/SKILL.md`    |
| Work in the Cluster_34 area (5 symbols)      | `.claude/skills/gitnexus-area-cluster-34/SKILL.md`    |
| Work in the Cluster_54 area (5 symbols)      | `.claude/skills/gitnexus-area-cluster-54/SKILL.md`    |
| Work in the Cluster_36 area (4 symbols)      | `.claude/skills/gitnexus-area-cluster-36/SKILL.md`    |
| Work in the Cluster_38 area (4 symbols)      | `.claude/skills/gitnexus-area-cluster-38/SKILL.md`    |
| Work in the Cluster_73 area (4 symbols)      | `.claude/skills/gitnexus-area-cluster-73/SKILL.md`    |
| Work in the Cluster_74 area (4 symbols)      | `.claude/skills/gitnexus-area-cluster-74/SKILL.md`    |
| Work in the Cluster_0 area (3 symbols)       | `.claude/skills/gitnexus-area-cluster-0/SKILL.md`     |

<!-- gitnexus:end -->

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues via the `gh` CLI (Linear syncs downstream
from GitHub). See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage roles, label strings equal to role names; the pre-existing
`wontfix` label is reused as-is. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root, created
lazily by `/domain-modeling`. See `docs/agents/domain.md`.
