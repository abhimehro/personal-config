# Maintenance Performance Engineering

Optimize background maintenance agents for minimal system impact.

## Best Practices
- **Smart Scheduling**: Use `StartCalendarInterval` in LaunchAgents to avoid peak hours.
- **Resource Gating**: Check system load and battery status before heavy operations.
- **Incremental Cleanup**: Clean caches based on file age to avoid massive I/O bursts.
- **Efficient Logging**: Use centralized, rotated logs to prevent disk bloat.

## Monitoring
- Track script duration in `SUMMARY_RESULTS`.
- Monitor world-writable file counts as a proxy for script drift.

## Examples
- `maintenance/bin/run_all_maintenance.sh`: Implements parallel execution for independent tasks.
- `maintenance/bin/quick_cleanup.sh`: Uses `find -mtime` to target only old files.
