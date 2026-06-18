# MCP server configuration

Single source of truth + generators for Model Context Protocol (MCP) servers
across every client on this machine: **Ara, Cursor, Windsurf, Windsurf Next,
Raycast AI**, and **Vibe**.

## Source of truth

| File                        | Role                                             | Secrets                                       |
| --------------------------- | ------------------------------------------------ | --------------------------------------------- |
| `mcp-servers.template.json` | **Canonical** server list. Committed.            | `op://` references only — **never** live keys |
| `mcp-servers.template`      | Legacy flat copy (kept for reference)            | refs only                                     |
| `servers.local.json`        | Optional hand-maintained local file (gitignored) | may contain live keys                         |

Edit **`mcp-servers.template.json`** to add/remove a server or change args. Then
regenerate the per-client runtime configs (below). Never put a real key in a
committed file.

## Generated runtime configs (live secrets, NOT committed)

`scripts/generate-mcp-configs.sh` reads the canonical template, resolves every
`op://` reference with **1Password** (`op inject`) — or **Proton Pass**
(`pass-cli inject`) — and writes a correctly-formatted config to each client's
real config path. Every generated file holds **live secrets**, is `chmod 600`,
and lives **outside this repo** (in the app's own config dir), so git never sees
it.

| Client        | Generated path                                | Wrapper key  | Remote-URL key                                  |
| ------------- | --------------------------------------------- | ------------ | ----------------------------------------------- |
| Ara           | `~/.ara/mcp-servers.json`                     | _(flat)_     | `url`                                           |
| Cursor        | `~/.cursor/mcp.json`                          | `mcpServers` | `url`                                           |
| Windsurf      | `~/.codeium/windsurf/mcp_config.json`         | `mcpServers` | `serverUrl`                                     |
| Windsurf Next | `~/.codeium/windsurf-next/mcp_config.json`    | `mcpServers` | `serverUrl`                                     |
| Raycast AI    | `~/.config/raycast/ai/mcp-servers.local.json` | `mcpServers` | `url`                                           |
| Vibe          | `~/.vibe/mcp-servers.json`                    | _(flat)_     | `url` — already uses `op://`, resolved natively |

> **Format gotcha:** Windsurf uses `serverUrl` for remote (HTTP/SSE) servers,
> while everyone else uses `url`. The generator handles this automatically — do
> not hand-edit.

## How to regenerate

```bash
# All clients, 1Password backend (default — current source of truth)
./scripts/generate-mcp-configs.sh

# Specific clients only
./scripts/generate-mcp-configs.sh ara cursor

# Use Proton Pass as the secret backend instead of 1Password
./scripts/generate-mcp-configs.sh --backend proton
```

Before regenerating, make sure your secret backend is unlocked:

- **1Password:** `op signin` (or system/biometric unlock). Verify:
  `op read op://Personal/BRAVE_API_KEY/credential`
- **Proton Pass:** `pass-cli info` should exit 0. If not, see "Proton Pass"
  below.

Each run backs up the previous config to `~/.config/mcp-backups/` (0700 dir,
0600 files) before overwriting.

## Raycast (extra step)

Raycast AI does not auto-read a file path. After generating, open Raycast →
**Manage MCP Servers** → import `~/.config/raycast/ai/mcp-servers.local.json`.

## Secret backends — running both

Both backends are wired up; **1Password remains the source of truth**, Proton
Pass is a parallel path.

### 1Password (primary)

References look like `op://Personal/<ITEM>/credential`. Resolved by `op inject`
at generate time. Required refs: `BRAVE_API_KEY`, `EXA_API_KEY`,
`FIRECRAWL_API_KEY`, `PERPLEXITY_RAYCAST_API_KEY`, `TAVILY_API_KEY`,
`GITHUB_PERSONAL_ACCESS_TOKEN`, `DEVIN_API_KEY`.

### Proton Pass (parallel)

`pass-cli` supports `inject` (template → secrets) and `run` (env injection),
plus AI-agent **Personal Access Tokens (PATs)**. To use it as a backend, switch
the template's secret refs to `pass://SHARE_ID/ITEM_ID` form (or keep a parallel
template) and run with `--backend proton`.

Proton Pass is a **credential CLI, not a hosted MCP server** — there is no
`mcp.protonpass.*` endpoint to add as a server. `scripts/proton-pass-mcp.sh`
warms an isolated, authenticated `pass-cli` session (PAT read from
`op://Personal/PROTON_PASS_MCP_PAT/credential`) for agents that shell out to
`pass-cli` with `PROTON_PASS_AGENT_REASON` set.

Create / rotate an agent token:

```bash
pass-cli agent create --expiration 6m --vault Personal 'MCP Server'
# store the printed PAT in 1Password as PROTON_PASS_MCP_PAT, then:
pass-cli agent list
```

## Newly added servers

- **paste** — local HTTP MCP at `http://127.0.0.1:39725/mcp`
- **deepwiki** — `https://mcp.deepwiki.com/mcp`
- **devin** — `https://mcp.devin.ai/mcp` (Bearer
  `op://Personal/DEVIN_API_KEY/credential`)

## Security notes

- Committed files contain **only** `op://` / `pass://` references.
- Generated files (live keys) are `0600`, outside the repo, and covered by
  `.gitignore` patterns (`*mcp-config*.local.json`, `mcp-configs/*.local.json`).
- Backups live in `~/.config/mcp-backups/` (0700) — not in the repo.
- **2026-05-28:** Windsurf Next previously stored API keys in **plaintext**.
  Those configs were regenerated with `op://`-resolved keys at `0600`. The
  exposed keys (Brave, Exa, Tavily, GitHub PAT, Perplexity) **should be
  rotated**.
