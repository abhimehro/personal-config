#!/usr/bin/env python3
"""Filter MCP JSON and emit Vibe [[mcp_servers]] TOML.

Vibe 2.16.1 reads MCP from config.toml, not mcp-servers.json.
OAuth-only remote servers are skipped because Vibe does not support OAuth MCP.

Reads a flat {name: cfg} JSON object from stdin (template or injected).
Writes TOML to stdout. Never prints resolved secrets; callers should pass
templates with op:// refs, or inject only into untracked 0600 destinations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_DIR = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO_DIR / "ai" / "inventory" / "mcp-capabilities.json"

OAUTH_SKIP_DEFAULT = {
    "GitHub",
    "Linear",
    "Notion",
    "prisma",
    "linear-mcp-server",
    "prisma-mcp-server",
    "github-mcp-server",
}


def toml_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )


def toml_str(value: str) -> str:
    return f'"{toml_escape(value)}"'


def load_inventory(path: Path = INVENTORY_PATH) -> dict[str, Any]:
    if not path.is_file():
        return {"profiles": {}, "servers": {}}
    return json.loads(path.read_text())


def profile_allowlist(inventory: dict[str, Any], profile: str) -> set[str] | None:
    profiles = inventory.get("profiles") or {}
    spec = profiles.get(profile)
    if spec is None:
        raise SystemExit(f"unknown MCP profile: {profile}")
    servers = spec.get("servers") or []
    if servers == ["*"]:
        return None
    return set(servers)


def vibe_supported(inventory: dict[str, Any], name: str) -> bool:
    meta = (inventory.get("servers") or {}).get(name) or {}
    if "vibe_supported" in meta:
        return bool(meta["vibe_supported"])
    return name not in OAUTH_SKIP_DEFAULT


def slug(name: str) -> str:
    out = []
    for ch in name.strip():
        if ch.isalnum():
            out.append(ch.lower())
        else:
            out.append("_")
    compact = "".join(out).strip("_")
    while "__" in compact:
        compact = compact.replace("__", "_")
    return compact or "server"


def emit_server(name: str, cfg: dict[str, Any]) -> str:
    lines = ["[[mcp_servers]]", f"name = {toml_str(slug(name))}"]
    if cfg.get("command"):
        lines.append('transport = "stdio"')
        lines.append(f"command = {toml_str(str(cfg['command']))}")
        args = cfg.get("args") or []
        if args:
            inner = ", ".join(toml_str(str(a)) for a in args)
            lines.append(f"args = [{inner}]")
        env = cfg.get("env") or {}
        if env:
            lines.append("[mcp_servers.env]")
            for key, val in env.items():
                lines.append(f"{key} = {toml_str(str(val))}")
    else:
        url = cfg.get("url") or cfg.get("serverUrl")
        if not url:
            return ""
        lines.append('transport = "streamable-http"')
        lines.append(f"url = {toml_str(str(url))}")
        headers = cfg.get("headers") or {}
        if headers:
            lines.append("[mcp_servers.headers]")
            for key, val in headers.items():
                lines.append(f"{key} = {toml_str(str(val))}")
    lines.append("")
    return "\n".join(lines)


def filter_servers(
    data: dict[str, Any],
    inventory: dict[str, Any],
    profile: str,
) -> dict[str, Any]:
    allow = profile_allowlist(inventory, profile)
    out: dict[str, Any] = {}
    for name, cfg in data.items():
        if not isinstance(cfg, dict):
            continue
        if allow is not None and name not in allow:
            continue
        if not vibe_supported(inventory, name):
            continue
        out[name] = cfg
    return out


def render(data: dict[str, Any], inventory: dict[str, Any], profile: str) -> str:
    selected = filter_servers(data, inventory, profile)
    chunks = [
        "# Generated Vibe MCP fragment. Merge into ~/.vibe/config.toml.",
        f"# profile = {profile}",
        "# OAuth MCP servers are omitted (Vibe does not support OAuth).",
        "",
    ]
    for name in selected:
        block = emit_server(name, selected[name])
        if block:
            chunks.append(block)
    return "\n".join(chunks).rstrip() + "\n"


def main(argv: list[str]) -> int:
    profile = "core-safe"
    if len(argv) > 1:
        profile = argv[1]
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("stdin was empty; expected MCP JSON object")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise SystemExit("expected a JSON object of MCP servers")
    if "mcpServers" in data and isinstance(data["mcpServers"], dict):
        data = data["mcpServers"]
    inventory = load_inventory()
    sys.stdout.write(render(data, inventory, profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
