## 2024-10-27 - [Idempotent Service Switching]
**Learning:** Shell scripts managing services should be idempotent. Restarting a service when the desired configuration is already active is wasteful (latency, CPU, potential downtime).
**Action:** Always check `pgrep` and current configuration state (e.g., via symlink targets or grep) before initiating a stop/start cycle.
