# CI Performance Engineering

Optimize GitHub Actions workflows for rapid feedback and low minute consumption.

## Best Practices
- **Caching**: Use `actions/cache` for persistent tools (Trunk, ShellCheck).
- **Path Filtering**: Only trigger workflows if relevant files changed (e.g., `paths: ['*.sh']`).
- **Concurrent Runs**: Cancel outdated runs on the same PR using `concurrency` groups.
- **Efficient Environments**: Use `ubuntu-slim` or pre-configured images where possible.

## Caching Strategy
- **Trunk**: Cache `~/.cache/trunk` and `.trunk/out`.
- **ShellCheck**: Cache `~/.local/bin/shellcheck`.
- **Python**: Use `actions/setup-python` built-in `cache: 'pip'`.

## Success Metrics
- CI completion under 2 minutes.
- Cache hit rate > 80%.
