MCP server templates
====================

Files:
- `mcp-servers.template.json` — template for Cursor/Raycast/IDE MCP servers with placeholder API keys.
- `servers.local.json` — example local file (gitignored) prefilled with 1Password `op://` references for keys. Copy/adjust as needed.

How to use:
1) Copy the template to a local, gitignored file:
   - `cp mcp-configs/mcp-servers.template.json mcp-configs/servers.local.json`
2) Fill in your real API keys (keep out of git).
3) Point your client to the local file:
   - Cursor: add servers to your MCP configuration (do not commit secrets).
   - Raycast AI / other IDEs: import or reference the local JSON.

Git ignore:
- Patterns are added to `.gitignore` for `mcp-configs/*.local.json` and similar; keep secrets local.

1Password usage:
- Use 1Password item references (`op://...`) in your local file and run commands under `op run` or configure your client to resolve `op://` at runtime.
- Example: `"BRAVE_API_KEY": "op://Vault/Brave Search/api_key"` (adjust vault/item/field).
