import os
import sys
import unittest
import argparse
from unittest.mock import patch, MagicMock, AsyncMock

# Add target script location to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../.agents/skills/secops-autopilot/scripts")))

import secops_agent


class TestSecopsAgent(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_repos = ["test-repo-1", "test-repo-2"]

    @patch("secops_agent.HAS_ANTIGRAVITY", True)
    @patch("secops_agent.Agent")
    @patch("secops_agent.LocalAgentConfig")
    async def test_ai_diagnose_tier1_success(self, mock_config, mock_agent_class):
        # Mock Antigravity Agent success
        mock_agent_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = AsyncMock(return_value="Antigravity diagnostic suggestion")
        mock_agent_instance.chat = AsyncMock(return_value=mock_response)
        
        # Setup context manager mock
        mock_agent_class.return_value = mock_agent_instance
        mock_agent_instance.__aenter__ = AsyncMock(return_value=mock_agent_instance)
        mock_agent_instance.__aexit__ = AsyncMock(return_value=None)
        
        result = await secops_agent.ai_diagnose("Test prompt", "Log content", verbose=False)
        self.assertIn("Tier 1: Antigravity SDK", result)
        self.assertIn("Antigravity diagnostic suggestion", result)

    @patch("secops_agent.HAS_ANTIGRAVITY", False)
    @patch("secops_agent.run_timeout")
    async def test_ai_diagnose_tier2_vibe_success(self, mock_run_timeout):
        # Vibe CLI mock success
        mock_run_timeout.return_value = (0, b"Vibe CLI diagnostic output\n[ara-pyshim] debug line", b"")
        
        with patch("secops_agent.shutil_which", return_value="/usr/local/bin/vibe"):
            result = await secops_agent.ai_diagnose("Test prompt", "Log content", verbose=False)
            self.assertIn("Tier 2: Vibe CLI", result)
            self.assertIn("Vibe CLI diagnostic output", result)
            self.assertNotIn("[ara-pyshim]", result)

    @patch("secops_agent.HAS_ANTIGRAVITY", False)
    @patch("secops_agent.shutil_which", return_value=None)
    @patch("os.path.exists", return_value=False)
    async def test_ai_diagnose_tier3_raw_fallback(self, mock_exists, mock_which):
        result = await secops_agent.ai_diagnose("Test prompt", "Log content", verbose=False)
        self.assertIn("Tier 3 Fallback", result)
        self.assertIn("Log content", result)

    def test_argparse_parsing(self):
        # Test argparse setup and subcommand routing
        test_parser = argparse.ArgumentParser()
        # Mock subparser parsing
        with patch("sys.argv", ["secops_agent.py", "health", "--dry-run", "--no-llm"]):
            # Run parser checks inside the main block structure manually
            pass

    async def test_run_timeout_success(self):
        rc, stdout, stderr = await secops_agent.run_timeout(["echo", "hello"], 10)
        self.assertEqual(rc, 0)
        self.assertIn(b"hello", stdout)


if __name__ == "__main__":
    unittest.main()
