# RepoPrompt Agent Skills

This directory contains agent skills and workflows for **RepoPrompt**, a context-aware development tool.

## Directory Structure

```
.agents/skills/
├── rp-build/          # Build workflow with context builder
├── rp-build-cli/      # CLI version of build workflow
├── rp-investigate/    # Deep investigation workflow
├── rp-investigate-cli/# CLI version of investigation
├── rp-oracle-export/  # Export prompts for external use
├── rp-refactor/       # Code refactoring assistance
├── rp-reminder/       # Reminder workflows
└── rp-review/         # Code review workflows
```

## Intentional Duplication

The content in this directory is **intentionally duplicated** in `.claude/skills/` for Claude Code's skill system. Both directories contain the same skills but are loaded by different tools:

- `.agents/skills/` → Loaded by RepoPrompt

- `.claude/skills/` → Loaded by Claude Code

This separation allows each tool to access the same workflow definitions in their native format.

## Usage

These skills are automatically available when using RepoPrompt with this workspace. Each skill includes:

- `SKILL.md` - The skill definition and instructions
- `agents/` - Agent configuration files (e.g., OpenAI YAML configs)

## Management

Skills are managed by RepoPrompt and should not be manually edited unless updating the workflow definitions.
