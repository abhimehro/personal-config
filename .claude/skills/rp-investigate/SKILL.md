---
name: "rp-investigate"
description: "Deep investigation with RepoPrompt MCP tools: tools gather evidence, follow-up reasoning synthesizes selected context"
repoprompt_managed: true
repoprompt_skills_version: 29
repoprompt_variant: mcp
---

# Deep Investigation Mode

Investigate: $ARGUMENTS

You are now in deep investigation mode for the issue described above. Follow this protocol rigorously.

## Investigation Protocol

This workflow leverages three complementary capabilities:

- **You (the agent)**: Can read any file with exact line numbers, run git commands, search the codebase, run experiments, and produce concrete evidence. You can also **mutate the file selection** to control what the chat sees. You are the hands and eyes.
- **Context Builder** (`context_builder`): Explores the codebase and **populates the file selection** — choosing full files or slices of files relevant to the task. This is its primary output: a curated selection the chat can analyze.
- **Chat** (`chat_send`): Deep analytical reasoning over **the current file selection**. It sees selected files **completely** (full content, not summaries), but it **only sees what's in the selection** — nothing else. It excels at synthesizing patterns, spotting architectural issues, and forming hypotheses from the big picture. It is **not** a lookup tool: if a question can be answered by reading files, searching, or running git/tool calls, do that yourself first.

### How File Selection Drives the Workflow

The **file selection** is the shared context between you, the context builder, and the chat:
1. `context_builder` populates the selection with relevant files/slices it discovers
2. The chat analyzes whatever is currently selected — it has no other view of the codebase
3. You can **add or remove** specific files via `manage_selection` to augment or refine what the chat sees
4. You can **add slices** of large files to supplement the selection without blowing the token budget

**Important:** The context builder operates with a large token budget and works hard to maximize useful context. Don't constrain it — build on its selection with targeted `add`/`remove` calls rather than replacing it.

### Core Principles
1. **Don't stop until confident** — pursue every lead until you have solid evidence
2. **Play to each tool's strengths** — context builder for broad discovery, the chat for deep analysis, your own tools for precise evidence gathering
3. **You produce the evidence** — the chat analyzes and hypothesizes; you verify with exact file reads, git blame, searches
4. **Manage the selection actively** — refocus the chat on different files as the investigation narrows
5. **Use tool calls for facts, chat for synthesis** — resolve straightforward lookups yourself before asking for analytical help
6. **Document findings as you go** — create/update a report file with observations

### Phase 0: Workspace Verification (REQUIRED)

Before any investigation, confirm the target codebase is loaded:

```json
{"tool":"list_windows","args":{}}
```

**Check the output:**
- If your target root appears in a window → bind to that window with `select_window`
- If not → the codebase isn't loaded

**Bind to the correct window:**
```json
{"tool":"select_window","args":{"window_id":<window_id_with_your_root>}}
```

**If the root isn't loaded**, find and open the workspace:
```json
{"tool":"manage_workspaces","args":{"action":"list"}}
{"tool":"manage_workspaces","args":{"action":"switch","workspace":"<workspace_name>","open_in_new_window":true}}
```

---
### Phase 1: Initial Assessment (Agent — you)

1. Read any provided files/reports (traces, logs, error reports)
2. Summarize the symptoms and constraints
3. Form initial hypotheses
4. Do a brief search or two if needed to orient yourself

Keep this short — save deep exploration for after `context_builder`.

### Phase 2: Broad Context Gathering (via `context_builder` — REQUIRED)

⚠️ **Do NOT skip this step.** The context builder discovers relevant files across the codebase that you'd miss with manual searching. It populates the file selection with full files or targeted slices.

Use `context_builder` with detailed instructions describing what to investigate and why:

```
mcp__RepoPrompt__context_builder:
  instructions: |
	<task>Describe the specific issue or question to investigate</task>

	<context>
    Symptoms observed:
	- <concrete symptom 1>
	- <concrete symptom 2>

    Hypotheses to test:
	- <theory 1>
	- <theory 2>

	Areas likely involved:
	- <specific files, patterns, or subsystems>
	</context>

	response_type: question
```

Use `response_type: question` so the chat immediately analyzes the gathered context and returns its initial assessment.

### Phase 3: Agent Verification & Evidence Gathering (Agent — you)

The chat's response will contain hypotheses and analytical pointers. **Your job is to verify them with precision:**

- **Read specific files** the chat mentioned — check exact implementations and line numbers
- **Search for patterns** the chat identified — confirm they exist where expected
- **Run git blame/log** on suspicious areas — find when changes were introduced
- **Trace data/control flow** through code paths the chat flagged
- **Check for edge cases** the chat hypothesized about

Build a concrete evidence list: file paths, line numbers, git commits, actual code snippets.

If a factual gap can be closed with `read_file`, `file_search`, `git`, or another direct tool call, do that before going back to the chat.

### Phase 4: Refocused Chat Deep Dives (Iterate)

Update the selection to focus the chat on what matters now, then ask targeted questions that require synthesis rather than direct lookup:

```
// Add files the chat hasn't seen yet
mcp__RepoPrompt__manage_selection:
	op: add
	paths: [<additional files relevant to the current hypothesis>]

// Or add a slice of a large file
mcp__RepoPrompt__manage_selection:
	op: add
	slices:
	- path: "Root/large/file.swift"
		ranges: [{start_line: 100, end_line: 250}]

// Then ask a focused question — the chat will see the updated selection
mcp__RepoPrompt__`chat_send`:
  chat_id: <from context_builder>
	message: |
	Based on my investigation, here's what I found:
	- <concrete evidence 1 with file:line>
	- <concrete evidence 2 with file:line>

	Given this evidence, <specific analytical question>
	mode: chat
```

**Repeat Phases 3–4** as needed, but be judicious. The chat is slow and resource-intensive — do substantial reasoning and evidence gathering on your own between calls. Don't invoke it just to ask a quick question you could answer yourself with `read_file`, `file_search`, `git`, or other direct tool calls. Reserve it for moments when you need deep analytical synthesis, competing explanations, or cross-file reasoning across the selected context.

### Phase 5: Conclusions & Report (Agent — you)

You write the final report with precise references. The chat reasons about patterns but can't produce exact line numbers — that's your job.

Document:
- **Root cause** — with exact file paths, line numbers, and code snippets as evidence
- **Eliminated hypotheses** — and what evidence ruled them out
- **Recommended fixes** — specific, actionable changes with file locations
- **Preventive measures** — how to avoid this in future

---

## Role Summary

| Capability | Agent (you) | Context Builder | Chat (`chat_send`) |
|------------|-------------|-----------------|--------|
| Discover relevant files broadly | ❌ Limited | ✅ Primary | ❌ |
| Populate file selection | ❌ | ✅ Primary | ❌ |
| Read exact file contents & lines | ✅ Primary | ❌ | Sees full selected files |
| Run git blame/log/diff | ✅ | ❌ | ❌ |
| Search across codebase | ✅ | ✅ | ❌ |
| Synthesize patterns & architecture | ⚠️ OK | ❌ | ✅ Primary |
| Form & refine hypotheses | ⚠️ OK | ❌ | ✅ Primary |
| Produce line-number evidence | ✅ Primary | ❌ | ❌ |
| Mutate selection to refocus chat | ✅ | ❌ | ❌ |

---

## Report Template

Create a findings report as you investigate:

```markdown
# Investigation: [Title]

## Summary
[1-2 sentence summary of findings]

## Symptoms
- [Observed symptom 1]
- [Observed symptom 2]

## Investigation Log

### [Phase] - [Area Investigated]
**Hypothesis:** [What you were testing]
**Findings:** [What you found]
**Evidence:** [Exact file paths, line numbers, code snippets, git commits]
**Conclusion:** [Confirmed/Eliminated/Needs more investigation]

## Root Cause
[Detailed explanation with precise evidence]

## Recommendations
1. [Fix 1 — specific file and location]
2. [Fix 2 — specific file and location]

## Preventive Measures
- [How to prevent this in future]
```

---

## Anti-patterns to Avoid

- 🚫 **CRITICAL:** Skipping `context_builder` and attempting to investigate by reading files manually — you'll miss critical context
- 🚫 Skipping Phase 0 (Workspace Verification) — you must confirm the target codebase is loaded first
- 🚫 Asking the chat to produce exact line numbers — it sees full file content but without reliable line numbering; that's YOUR job
- 🚫 Doing extensive exploration (5+ tool calls) before calling `context_builder` — initial assessment should be brief
- 🚫 Drawing conclusions before gathering concrete evidence yourself
- 🚫 Not feeding your evidence back to the chat — it needs your findings to refine its analysis
- 🚫 Calling the chat repeatedly without doing your own investigation in between — do substantial work between calls
- 🚫 Invoking the chat for questions you could answer with `read_file`, `file_search`, `git`, or other direct tool calls — reserve it for deep analytical synthesis
- 🚫 Using `manage_selection` with `op:"clear"` or `op:"set"` — this undoes `context_builder`'s carefully curated selection; use `op:"add"` and `op:"remove"` to build on it

---

Now begin the investigation. Read any provided context, form initial hypotheses, then **immediately** use `context_builder` to gather broad context. After that, alternate between your own evidence gathering and refocused chat deep dives.