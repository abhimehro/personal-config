# ClickHouse Cursor plugin

Cursor plugin that adds **ClickHouse skills** and **MCP** support.

## What’s included

- **Skills** – `skills` is a symlink to `submodules/agent-skills/skills` (ClickHouse best-practices from [ClickHouse/agent-skills](https://github.com/ClickHouse/agent-skills)).
- **MCP** – ClickHouse MCP server config in `mcp.json`.

## Prerequisites

- **MCP** – Enable MCP on your ClickHouse service. See [Enable MCP on ClickHouse](https://clickhouse.com/docs/use-cases/AI/MCP/remote_mcp).

## How to use

After the plugin is installed from the **Cursor Marketplace**, its skills and MCP are available to Cursor’s agent.

- **ClickHouse best-practices** – When you’re writing or editing ClickHouse SQL, schemas, or ingestion logic, the agent can use this skill automatically. You can also ask explicitly, e.g. *“Check this query against ClickHouse best practices.”*
- **MCP** – The plugin’s `mcp.json` configures the ClickHouse MCP server (HTTP endpoint). Once the plugin is installed and you’ve authenticated (and [MCP is enabled on your service](https://clickhouse.com/docs/use-cases/AI/MCP/remote_mcp)), Cursor can use it to run queries, inspect schemas, or otherwise interact with ClickHouse when the agent needs it. Configure any required credentials or endpoints in Cursor’s MCP settings if your setup needs them.

## Install

Install the **ClickHouse Cursor** plugin from the **Cursor Marketplace**. 
Once installed, follow the prompt to authenticate with your ClickHouse account using OAuth.

## Development

If you clone or fork this repo (e.g. to contribute or customize), use submodules so the `skills` symlink resolves (submodule lives at `submodules/agent-skills`):

```bash
git clone --recurse-submodules https://github.com/ClickHouse/clickhouse-cursor-plugin.git
```

## License

Apache 2.0. See [LICENSE](LICENSE).
