## 2025-10-27 - [Unsafe DNS Listener Binding]
**Vulnerability:** The `controld-manager` script was configured to bind the DNS listener to `0.0.0.0` (all interfaces) instead of `127.0.0.1` (localhost).
**Learning:** Hardcoding `0.0.0.0` as a "fix" for connectivity issues blindly exposes services to the entire local network (and potentially the internet), increasing the attack surface (DNS amplification, snooping). Local services should strictly bind to localhost unless explicitly designed for serving the network.
**Prevention:** Always default to binding to `127.0.0.1` for local system services. If a service needs to be accessible from other devices, use a specific LAN IP or require an explicit configuration flag/confirmation.
