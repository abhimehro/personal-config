# GitHub MCP Integration for Repository Automation

This document describes how to use the GitHub MCP (Model Context Protocol) server with the repository automation scripts to avoid SSH agent stalls when using the `gh` CLI.

## Overview

The repository automation scripts have been updated with a compatibility layer that allows them to use either:

- The traditional `gh` CLI (default)
- The GitHub MCP server (when enabled)

The MCP server provides the same functionality as the `gh` CLI but without the SSH agent dependency issues that can cause stalls in background terminals.

## Enabling MCP Mode

To enable MCP mode, set the `USE_MCP_GITHUB` environment variable:

```bash
export USE_MCP_GITHUB=true
python .github/scripts/repository_automation.py workflow-updater
```

Or for a single command:

```bash
USE_MCP_GITHUB=true python .github/scripts/repository_automation.py workflow-updater
```

## Requirements

To use MCP mode, you need:

1. The GitHub MCP server installed and configured
2. The MCP server available in your Python environment
3. Proper authentication configured for the MCP server

## Current MCP Coverage

The following functions have MCP compatibility:

- `latest_tag_for_action()` - Gets the latest release tag for a GitHub Action
- `tag_exists()` - Checks if a specific tag exists in a repository
- `mcp_json()` - Compatibility layer for `gh_json()` calls
- `mcp_text()` - Compatibility layer for `gh_text()` calls

Functions not yet migrated will automatically fall back to using the `gh` CLI.

## Benefits

- **No SSH agent stalls**: MCP doesn't rely on SSH authentication
- **Same API**: Existing scripts work without modification
- **Graceful fallback**: If MCP is unavailable, scripts fall back to `gh` CLI
- **Gradual migration**: You can enable MCP for specific operations

## Troubleshooting

If MCP mode doesn't work:

1. Check that the MCP server is installed: `pip install mcp-github`
2. Verify the MCP server is running
3. Check authentication: Ensure your MCP server has proper GitHub access
4. Fallback: The scripts will automatically use `gh` CLI if MCP fails

## Configuration in CI/CD

To use MCP in GitHub Actions, you would need to:

1. Install the MCP server in the workflow
2. Set the environment variable
3. Configure authentication (typically via a token)

Example:

```yaml
- name: Install MCP GitHub server
  run: pip install mcp-github

- name: Run automation with MCP
  env:
    USE_MCP_GITHUB: true
  run: python .github/scripts/repository_automation.py workflow-updater
```

Note: The `gh` CLI is still the default and recommended for most CI/CD scenarios as it's pre-installed in GitHub Actions runners.
