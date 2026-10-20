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

        with tempfile.TemporaryDirectory() as mount_dir:
            pathlib.Path(mount_dir, "fixture").touch()
            with (
                patch.object(
                    bootstrap_jellyfin_local,
                    "public_info",
                    return_value={"StartupWizardCompleted": True},
                ),
                patch.object(
                    bootstrap_jellyfin_local,
                    "MOUNT",
                    pathlib.Path(mount_dir),
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
                patch.object(
                    bootstrap_jellyfin_local, "wait_for_items", return_value=3
                ),
                patch.object(bootstrap_jellyfin_local, "http"),
                contextlib.redirect_stdout(output),
            ):
                result = bootstrap_jellyfin_local.main()

        out = output.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("DONE items=3 url=", out)
        for secret in (
            "user=",
            "creds=",
            username,
            credential_path,
            "sensitive-password",
            "sensitive-token",
        ):
            self.assertNotIn(secret, out)

    @patch("subprocess.run")
    def test_lc_run_uses_timeout(self, mock_run):
        mock_run.return_value = unittest.mock.MagicMock(returncode=0)
        with tempfile.NamedTemporaryFile("w") as tmp_sys_xml:
            tmp_sys_xml.write("<IsStartupWizardCompleted>true</IsStartupWizardCompleted>")
            tmp_sys_xml.flush()
            with (
                patch.object(
                    bootstrap_jellyfin_local,
                    "_launchctl_bin",
                    return_value="/bin/launchctl",
                ),
                patch.object(
                    bootstrap_jellyfin_local,
                    "SYSTEM_XML",
                    pathlib.Path(tmp_sys_xml.name),
                ),
                patch.object(
                    bootstrap_jellyfin_local,
                    "public_info",
                    return_value={"StartupWizardCompleted": False},
                ),
            ):
                bootstrap_jellyfin_local.reset_wizard_flag()

        self.assertTrue(mock_run.called)
        for call_args in mock_run.call_args_list:
            kwargs = call_args.kwargs
            self.assertIn("timeout", kwargs)
            self.assertEqual(kwargs["timeout"], 30)


if __name__ == "__main__":
    unittest.main()
