"""Regression tests for the local Jellyfin bootstrap script."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import pathlib
import tempfile
import unittest
from unittest.mock import patch


_SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1]
    / "media-streaming"
    / "scripts"
    / "bootstrap-jellyfin-local.py"
)
_SPEC = importlib.util.spec_from_file_location("bootstrap_jellyfin_local", _SCRIPT)
bootstrap_jellyfin_local = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(bootstrap_jellyfin_local)


class TestBootstrapJellyfinLocal(unittest.TestCase):
    def test_completion_log_does_not_expose_credentials(self):
        username = "sensitive-user"
        credential_path = str(bootstrap_jellyfin_local.CREDS)
        output = io.StringIO()

        with (
            patch.object(
                bootstrap_jellyfin_local,
                "public_info",
                return_value={"StartupWizardCompleted": True},
            ),
            patch.object(
                bootstrap_jellyfin_local,
                "MOUNT",
                pathlib.Path("/tmp"),
            ),
            patch.object(
                bootstrap_jellyfin_local,
                "load_or_create_creds",
                return_value=(username, "sensitive-password"),
            ),
            patch.object(
                bootstrap_jellyfin_local,
                "ensure_admin",
                return_value="sensitive-token",
            ),
            patch.object(bootstrap_jellyfin_local, "ensure_library"),
            patch.object(bootstrap_jellyfin_local, "wait_for_items", return_value=3),
            patch.object(bootstrap_jellyfin_local, "http"),
            contextlib.redirect_stdout(output),
        ):
            result = bootstrap_jellyfin_local.main()

        self.assertEqual(result, 0)
        self.assertIn("DONE items=3 url=", output.getvalue())
        self.assertNotIn(username, output.getvalue())
        self.assertNotIn(credential_path, output.getvalue())
        self.assertNotIn("sensitive-password", output.getvalue())
        self.assertNotIn("sensitive-token", output.getvalue())


if __name__ == "__main__":
    unittest.main()
