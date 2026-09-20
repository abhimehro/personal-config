#!/usr/bin/env python3
"""Tests for scripts/mcp_vibe_toml.py (no live secrets)."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO / "scripts" / "mcp_vibe_toml.py"


def load_module():
    spec = importlib.util.spec_from_file_location("mcp_vibe_toml", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestMcpVibeToml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()
        cls.inventory = json.loads(
            (REPO / "ai" / "inventory" / "mcp-capabilities.json").read_text()
        )
        cls.template = json.loads(
            (REPO / "mcp-configs" / "mcp-servers.template.json").read_text()
        )

    def test_core_safe_skips_oauth_and_paid_search(self):
        selected = self.mod.filter_servers(self.template, self.inventory, "core-safe")
        self.assertIn("Context7", selected)
        self.assertIn("paste", selected)
        self.assertIn("deepwiki", selected)
        self.assertNotIn("GitHub", selected)
        self.assertNotIn("Brave Search", selected)
        self.assertNotIn("Tavily", selected)
        self.assertNotIn("Filesystem", selected)
        self.assertNotIn("applescript_execute", selected)

    def test_research_adds_firecrawl_only(self):
        selected = self.mod.filter_servers(self.template, self.inventory, "research")
        self.assertIn("firecrawl-mcp", selected)
        self.assertNotIn("Exa", selected)
        self.assertNotIn("Perplexity", selected)

    def test_unknown_profile_exits(self):
        with self.assertRaises(SystemExit):
            self.mod.profile_allowlist(self.inventory, "not-a-profile")

    def test_toml_has_no_live_key_literals(self):
        text = self.mod.render(self.template, self.inventory, "research")
        self.assertIn("[[mcp_servers]]", text)
        self.assertIn("transport =", text)
        self.assertNotRegex(text, r"sk-[A-Za-z0-9]+")
        self.assertNotRegex(text, r"ghp_[A-Za-z0-9]+")
        self.assertIn("op://", text)
        self.assertNotIn("GitHub", text)

    def test_stdio_and_http_blocks(self):
        data = {
            "Context7": {
                "command": "npx",
                "args": ["-y", "@upstash/context7-mcp"],
                "env": {},
            },
            "paste": {"url": "http://127.0.0.1:39725/mcp"},
            "GitHub": {"url": "https://api.githubcopilot.com/mcp/"},
        }
        text = self.mod.render(data, self.inventory, "core-safe")
        self.assertIn('name = "context7"', text)
        self.assertIn('transport = "stdio"', text)
        self.assertIn('name = "paste"', text)
        self.assertIn('transport = "streamable-http"', text)
        self.assertNotIn("githubcopilot", text)

    def test_toml_escape(self):
        self.assertEqual(self.mod.toml_str('a"b'), '"a\\"b"')

    def test_inventory_matches_template_names_for_defaults(self):
        servers = self.inventory["servers"]
        for name in self.inventory["profiles"]["core-safe"]["servers"]:
            self.assertIn(name, servers)


class TestInventoryFile(unittest.TestCase):
    def test_json_valid_and_secret_free(self):
        raw = (REPO / "ai" / "inventory" / "mcp-capabilities.json").read_text()
        data = json.loads(raw)
        self.assertIn("profiles", data)
        self.assertIn("core-safe", data["profiles"])
        self.assertNotIn("sk-", raw)
        self.assertNotIn("ghp_", raw)
        self.assertNotIn("Bearer ey", raw)


class TestAdapterFiles(unittest.TestCase):
    def test_vibe_fragment_disables_bypass(self):
        text = (REPO / "ai" / "adapters" / "vibe" / "config.core-safe.toml").read_text()
        self.assertIn("bypass_tool_permissions = false", text)
        self.assertNotRegex(text, r"(?m)^bypass_tool_permissions = true")

    def test_cursor_adapter_is_allowlist(self):
        data = json.loads(
            (REPO / "ai" / "adapters" / "cursor" / "cli.json").read_text()
        )
        self.assertEqual(data["approvalMode"], "allowlist")
        self.assertNotEqual(data["approvalMode"], "unrestricted")
        self.assertIn("deny", data["permissions"])

    def test_antigravity_adapter_asks(self):
        data = json.loads(
            (
                REPO / "ai" / "adapters" / "antigravity" / "settings.safe.json"
            ).read_text()
        )
        self.assertEqual(data["toolPermission"], "request-review")
        self.assertFalse(data["allowNonWorkspaceAccess"])


class TestGeneratorScript(unittest.TestCase):
    """Bounded dry-run tests for scripts/generate-mcp-configs.sh (no live writes)."""

    SCRIPT = REPO / "scripts" / "generate-mcp-configs.sh"

    def _run(self, *args):
        import subprocess  # nosec B404 - fixed argv, repo-owned script only

        proc = subprocess.run(  # nosec B603, B607 - trusted repo script, no shell
            ["/bin/bash", str(self.SCRIPT), *args],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO),
        )
        return proc

    def test_parser_accepts_vibe_dry_run(self):
        proc = self._run("--dry-run", "vibe")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Vibe: dry-run fragment", proc.stdout)
        self.assertIn("Dry-run complete", proc.stdout)

    def test_all_expansion_excludes_vibe(self):
        proc = self._run("--dry-run", "all")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Antigravity: dry-run", proc.stdout)
        self.assertNotIn("Vibe: dry-run", proc.stdout)
        self.assertNotIn("config.toml", proc.stdout)

    def test_dry_run_writes_no_live_paths(self):
        vibe_frag = Path.home() / ".vibe" / "mcp.fragment.toml"
        existed = vibe_frag.exists()
        mtime_before = vibe_frag.stat().st_mtime if existed else None
        proc = self._run("--dry-run", "vibe")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        if existed:
            self.assertEqual(vibe_frag.stat().st_mtime, mtime_before)
        else:
            self.assertFalse(vibe_frag.exists())

    def test_dry_run_does_not_invoke_secret_backend(self):
        proc = self._run("--dry-run", "vibe")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("op inject", proc.stdout)
        self.assertNotIn("pass-cli", proc.stdout)

    def test_unknown_target_fails_fast(self):
        proc = self._run("--dry-run", "bogus-target")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Unknown arg", proc.stderr)

    def test_unknown_profile_fails_safely(self):
        proc = self._run("--dry-run", "--profile", "bogus-profile", "vibe")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unknown MCP profile", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
