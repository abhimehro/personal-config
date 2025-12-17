## 2025-10-18 - [Insecure Local Media Sharing]
**Vulnerability:** The `media-streaming/scripts/alldebrid-server.py` and `infuse-media-server.py` scripts expose the file system via HTTP on `0.0.0.0` without authentication.
**Learning:** These scripts are designed for local network sharing (Infuse integration) but lack basic security controls, relying solely on network trust. This is a significant gap if the device connects to untrusted networks.
**Prevention:** Always bind to `127.0.0.1` by default for development/local tools. If public/LAN access is needed, enforce authentication (Basic Auth or similar) or use secure tunneling.
