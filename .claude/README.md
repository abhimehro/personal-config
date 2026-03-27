# Claude Code Skills

This directory contains agent skills for **Claude Code**, an AI-powered development assistant.

## Directory Structure

```
.claude/skills/
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

The content in this directory is **intentionally duplicated** in `.agents/skills/` for RepoPrompt's workflow system. Both directories contain the same skills but are loaded by different tools:

- `.claude/skills/` → Loaded by Claude Code

- `.agents/skills/` → Loaded by RepoPrompt

This separation allows each tool to access the same workflow definitions in their native format.

## Usage

These skills are automatically available when using Claude Code with this workspace. Each skill includes:

- `SKILL.md` - The skill definition and instructions
- `agents/` - Agent configuration files (e.g., OpenAI YAML configs)

## Management

Skills are managed by Claude Code and should not be manually edited unless updating the workflow definitions.
