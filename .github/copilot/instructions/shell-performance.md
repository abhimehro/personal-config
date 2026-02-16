# Shell Script Performance Engineering

Optimize shell scripts for speed and efficiency in the `personal-config` repo.

## Best Practices
- **Minimize Subshells**: Use `${var#prefix}` instead of `$(echo $var | sed ...)`.
- **Parallel Execution**: Use `&` and `wait` for independent network tasks (e.g., `network-mode-verify.sh`).
- **Efficient Searching**: Prefer `rg` (ripgrep) over `grep -r` if available.
- **Avoid Repeated Calls**: Cache results of expensive commands like `sw_vers` or `sysctl`.

## Benchmarking
Use `hyperfine` to measure impact:
```bash
hyperfine --warmup 3 'scripts/network-mode-manager.sh status'
```

## Examples
- `scripts/network-mode-verify.sh`: Uses background `dig` commands to parallelize DNS checks.
- `maintenance/lib/common_fixed.sh`: Caches architecture and OS version detections.
