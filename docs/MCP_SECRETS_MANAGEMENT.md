# MCP Server Secrets Management

This document explains how to manage API keys and secrets for MCP (Model Context Protocol) servers securely.

## Overview

The repository tracks MCP server configurations as templates in `.cursor/mcp.json`, but actual API keys and secrets should never be committed to version control.

## Local Secrets Storage

### Primary Location: `~/.config/mcp-servers/mcp-config.json`

Your actual API keys should be stored in:

```bash
/Users/speedybee/.config/mcp-servers/mcp-config.json
```

This file is automatically loaded by Cursor and other MCP-compatible tools.

### Example Structure

```json
{
  "mcpServers": {
    "Brave Search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your_actual_brave_api_key_here"
      }
    },
    "Exa": {
      "command": "npx",
      "args": ["exa-mcp-server"],
      "env": {
        "EXA_API_KEY": "$EXA_API_KEY"
      }
    }
    // ... other servers with real API keys
  }
}
```

## Environment Variables Alternative

You can also use environment variables. Create a local `.env` file (never commit):

```bash
# Copy from .env.example and fill in real values
cp .env.example .env
# Edit .env with your actual API keys
```

Then reference them in your MCP config:

```json
"env": {
  "BRAVE_API_KEY": "$BRAVE_API_KEY",
  "EXA_API_KEY": "$EXA_API_KEY"
}
```

## Symlink Strategy for Multiple Workplaces

To use the same secrets across different workplaces (RepoPrompt, Windsurf, Cursor, Gemini CLI):

### Option 1: Symlink the entire config

```bash
# In each workplace's .cursor directory
ln -s ~/.config/mcp-servers/mcp-config.json .cursor/mcp.json
```

### Option 2: Use a script to copy/separate configs

Create `scripts/sync_mcp_config.sh`:

```bash
#!/bin/bash
# Sync MCP config to all workplaces
WORKPLACES=(
  "$HOME/dev/personal-config"
  "$HOME/dev/another-project"
  # Add more paths as needed
)

for workplace in "${WORKPLACES[@]}"; do
  if [ -d "$workplace/.cursor" ]; then
    cp ~/.config/mcp-servers/mcp-config.json "$workplace/.cursor/mcp.json"
    echo "Synced MCP config to $workplace"
  fi
done
```

## Required API Keys

Based on the current MCP configuration, you may need API keys for:

| Service      | Purpose         | URL                            |
| ------------ | --------------- | ------------------------------ |
| Brave Search | Web search      | <https://brave.com/search/api> |
| Exa          | Advanced search | <https://exa.ai>               |
| Firecrawl    | Web crawling    | <https://firecrawl.dev>        |
| Perplexity   | AI search       | <https://perplexity.ai>        |
| Tavily       | Research search | <https://tavily.com>           |

## Security Best Practices

- Never commit API keys to version control
- Use different keys for development vs production if applicable
- Rotate keys regularly through the respective service dashboards
- Use environment-specific configs (e.g., `mcp-config.dev.json`, `mcp-config.prod.json`)
- Audit access regularly to ensure no keys are exposed

## Troubleshooting

### MCP Server Not Starting

- Check that API keys are correctly set
- Verify the JSON syntax is valid
- Ensure the path to `~/.config/mcp-servers/mcp-config.json` is correct

### Keys Not Working

- Verify the key hasn't expired
- Check if the key has the required permissions
- Ensure you're not hitting rate limits

### Workplace-Specific Issues

- Each workplace may have its own MCP config
- Check which config file is being loaded
- Use the symlink strategy for consistency
