#!/usr/bin/env python3
"""
Unit tests for morning-brief security validations and secret safeguards.

Run with:
    python3 -m unittest tests.test_morning_brief_security -v
"""

import importlib.util
import os
import sys
import unittest
from pathlib import Path

# Load morning_brief module
_script = (
    Path(__file__).parent.parent / "scripts" / "morning-brief" / "morning-brief.py"
)
_spec = importlib.util.spec_from_file_location("morning_brief", _script)
mb = importlib.util.module_from_spec(_spec)
sys.modules["morning_brief"] = mb
_spec.loader.exec_module(mb)


# ============================================================
# Secret and Client Validation Tests
# ============================================================


class TestSanitizeSecret(unittest.TestCase):
    def test_valid_token(self):
        self.assertEqual(
            mb.sanitize_secret("pplx-1234567890abcdef"),
            "pplx-1234567890abcdef",
        )
        self.assertEqual(
            mb.sanitize_secret("lin_api_abcdef1234567890"),
            "lin_api_abcdef1234567890",
        )
        # Test backwards compatibility alias
        self.assertEqual(
            mb.validate_api_key("pplx-1234567890abcdef"),
            "pplx-1234567890abcdef",
        )

    def test_strips_surrounding_whitespace(self):
        self.assertEqual(
            mb.sanitize_secret("  valid_key_12345  "),
            "valid_key_12345",
        )

    def test_none_or_non_string(self):
        self.assertEqual(mb.sanitize_secret(None), "")
        self.assertEqual(mb.sanitize_secret(12345), "")
        self.assertEqual(mb.sanitize_secret([]), "")

    def test_empty_or_whitespace_only(self):
        self.assertEqual(mb.sanitize_secret(""), "")
        self.assertEqual(mb.sanitize_secret("   "), "")

    def test_length_boundaries(self):
        self.assertEqual(mb.sanitize_secret("k"), "k")
        too_long = "a" * 4097
        self.assertEqual(mb.sanitize_secret(too_long), "")
        valid_long = "a" * 4096
        self.assertEqual(mb.sanitize_secret(valid_long), valid_long)

    def test_rejects_crlf_and_control_chars(self):
        self.assertEqual(mb.sanitize_secret("key\r\ninjected: header"), "")
        self.assertEqual(mb.sanitize_secret("key\ninjected"), "")
        self.assertEqual(mb.sanitize_secret("key\0zero"), "")
        self.assertEqual(mb.sanitize_secret("key with spaces"), "")


class TestPerplexityClientInit(unittest.TestCase):
    def test_valid_key(self):
        client = mb.PerplexityClient("pplx-1234567890")
        self.assertTrue(client.enabled)
        self.assertEqual(client.api_key, "pplx-1234567890")

    def test_empty_key_fails_secure(self):
        client = mb.PerplexityClient("")
        self.assertFalse(client.enabled)
        self.assertEqual(client.api_key, "")

    def test_whitespace_key_fails_secure(self):
        client = mb.PerplexityClient("   ")
        self.assertFalse(client.enabled)
        self.assertEqual(client.api_key, "")

    def test_crlf_key_fails_secure(self):
        client = mb.PerplexityClient("validkey\r\nAuthorization: evil")
        self.assertFalse(client.enabled)
        self.assertEqual(client.api_key, "")


class TestLinearKeyFallback(unittest.TestCase):
    def setUp(self):
        self.orig_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)

    def test_linear_fallback_to_token_when_api_key_invalid(self):
        os.environ["READWISE_TOKEN"] = "token12345"
        os.environ["LINEAR_API_KEY"] = "   "
        os.environ["LINEAR_TOKEN"] = "lin_token_valid_123"
        config = mb.AppConfig.load(argv=["--dry-run"])
        self.assertEqual(config.linear_api_key, "lin_token_valid_123")

    def test_linear_fallback_to_token_when_api_key_has_crlf(self):
        os.environ["READWISE_TOKEN"] = "token12345"
        os.environ["LINEAR_API_KEY"] = "invalid\r\nkey"
        os.environ["LINEAR_TOKEN"] = "lin_token_valid_456"
        config = mb.AppConfig.load(argv=["--dry-run"])
        self.assertEqual(config.linear_api_key, "lin_token_valid_456")

    def test_linear_prefers_api_key_when_valid(self):
        os.environ["READWISE_TOKEN"] = "token12345"
        os.environ["LINEAR_API_KEY"] = "lin_api_valid_123"
        os.environ["LINEAR_TOKEN"] = "lin_token_valid_456"
        config = mb.AppConfig.load(argv=["--dry-run"])
        self.assertEqual(config.linear_api_key, "lin_api_valid_123")


if __name__ == "__main__":
    unittest.main()
