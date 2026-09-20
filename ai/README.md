# AI CLI hub

Portable, secret-free source of truth for coding CLIs on this machine:

- Antigravity (`agy`)
- Cursor CLI (`cursor-agent` / official `agent`)
- Mistral Vibe (`vibe`)
- GitHub CLI (`gh`)
- Devin CLI (`devin`)

Live API keys, OAuth tokens, and `hosts.yml` stay out of git. This hub records
**what** to enable, **why**, and **which adapter** each tool understands.

## Layout

| Path                                 | Role                                                              |
| ------------------------------------ | ----------------------------------------------------------------- |
| `ai/inventory/mcp-capabilities.json` | Canonical MCP catalog, cost, risk, client support                 |
| `ai/policies/permissions.json`       | Safer permission defaults (do not copy live unrestricted configs) |
| `ai/models/routing.json`             | Student-budget model routing                                      |
| `ai/cli-matrix.md`                   | Capability gaps vs official CLIs                                  |
| `ai/adapters/`                       | Tool-shaped, secret-free fragments                                |
| `mcp-configs/`                       | Existing MCP templates + generator                                |
| `.agents/skills/`                    | Shared Agent Skills (prefer over copying trees)                   |

## Profiles

Default is **`core-safe`**. Enable others only for a session or after approval.

| Profile            | Intent                | Default servers                                   |
| ------------------ | --------------------- | ------------------------------------------------- |
| `core-safe`        | Daily coding          | Context7, GitHub (OAuth clients), paste, deepwiki |
| `research`         | One paid crawl/search | core-safe + firecrawl-mcp                         |
| `browser`          | Browser automation    | core-safe + Playwright                            |
| `productivity`     | Linear/Notion         | core-safe + Linear + Notion (not Vibe)            |
| `macos-automation` | AppleScript           | opt-in, high risk                                 |
| `cloud`            | GCP/Firebase/Prisma   | opt-in, high risk                                 |
| `full`             | Legacy template       | do not use as portable default                    |

## Do not do

- Do not commit live keys or copy `~/.config/gh/hosts.yml`.
- Do not propagate Cursor `approvalMode: unrestricted` or Vibe
  `bypass_tool_permissions = true`.
- Do not enable every search MCP at once (Brave + Exa + Tavily + Perplexity).
- Do not grant Filesystem MCP all of `~/dev/`.
- Do not overwrite `~/.vibe/config.toml` or `~/.config/devin/mcp_config.json`
  from the generator. Write fragments, then merge after review.
- Do not copy entire skill trees into each tool. Point at `.agents/skills`.

## Generate MCP

```bash
# Existing JSON clients (writes 0600 live files outside git)
./scripts/generate-mcp-configs.sh cursor antigravity

# Vibe TOML fragment (secret-free env refs, does not overwrite ~/.vibe/config.toml)
./scripts/generate-mcp-configs.sh --profile core-safe vibe

# Dry-run any target
./scripts/generate-mcp-configs.sh --dry-run vibe
```

Vibe official MCP lives in `[[mcp_servers]]` inside `config.toml`, not
`~/.vibe/mcp-servers.json`. Treat that JSON file as legacy until Vibe documents
it.

## Apply adapters (manual, after review)

| Tool        | Portable fragment                            | Live path (do not blindly replace)                |
| ----------- | -------------------------------------------- | ------------------------------------------------- |
| Cursor CLI  | `ai/adapters/cursor/cli.json`                | `~/.cursor/cli-config.json` (machine-local)       |
| Vibe        | `ai/adapters/vibe/config.core-safe.toml`     | `~/.vibe/config.toml`                             |
| Vibe MCP    | generator fragment                           | merge into `~/.vibe/config.toml`                  |
| Devin hooks | `ai/adapters/devin/hooks.v1.json`            | copy to `.devin/hooks.v1.json` after schema check |
| GitHub CLI  | `ai/adapters/gh/config.yml`                  | `~/.config/gh/config.yml` (never `hosts.yml`)     |
| Antigravity | `ai/adapters/antigravity/settings.safe.json` | `~/.gemini/antigravity-cli/settings.json`         |

## Shared skills

Keep workflows in `.agents/skills/<name>/SKILL.md`. Devin, Vibe, and Antigravity
can read `.agents/skills` where officially supported. Do not duplicate the tree
into `~/.vibe/skills` or `.devin/skills` unless a tool cannot follow the shared
path.
