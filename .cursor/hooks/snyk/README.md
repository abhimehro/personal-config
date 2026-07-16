# Snyk Secure at Inception (vendored)

Vendored from the [Snyk Secure Development](https://github.com/snyk/studio-recipes)
Cursor plugin (`guardrail_directives/secure_at_inception/hooks_version/cursor/async_cli_version/`).

## Files

| Path | Role |
|------|------|
| `snyk_secure_at_inception.py` | `afterFileEdit` / `stop` entrypoint |
| `lib/scan_runner.py` | Background scan lifecycle |
| `lib/scan_worker.py` | `snyk code test` subprocess worker |

## Runtime requirements

- `python3` (3.8+)
- `snyk` CLI on `PATH` (optional — falls back to MCP follow-up guidance)
- Authenticated Snyk (`snyk auth` or `SNYK_TOKEN`)

## Invoked by

`.cursor/hooks/run-snyk-sai.sh` via project `.cursor/hooks.json`.
