#!/usr/bin/env python3
"""Transform a flat MCP server map into a client-specific config.

Reads resolved MCP JSON (flat {name: cfg}) from stdin, writes transformed
JSON to stdout.

argv[1] wrapper : "flat" | "mcpServers"
argv[2] urlkey  : "url" | "serverUrl"
"""

import json
import sys

wrapper, urlkey = sys.argv[1], sys.argv[2]
data = json.load(sys.stdin)

# Normalize the remote-url key name per client.
for _name, cfg in data.items():
    if urlkey == "serverUrl" and "url" in cfg:
        cfg["serverUrl"] = cfg.pop("url")
    elif urlkey == "url" and "serverUrl" in cfg:
        cfg["url"] = cfg.pop("serverUrl")

out = data if wrapper == "flat" else {"mcpServers": data}
print(json.dumps(out, indent=2))
