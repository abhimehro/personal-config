"""Regression checks for the native Jellyfin network boundary."""

from __future__ import annotations

import importlib.util
import ipaddress
import os
import pathlib
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "media-streaming/scripts/secure-jellyfin-network.py"
SPEC = importlib.util.spec_from_file_location("secure_jellyfin_network", SCRIPT)
secure_jellyfin_network = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(secure_jellyfin_network)


class TestSecureJellyfinNetwork(unittest.TestCase):
    def test_new_config_binds_only_loopback_and_lan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "config/network.xml"

            def address_for_interface(argv, **_kwargs):
                value = "192.168.0.111\n" if argv[-1] == "en5" else "203.0.113.9\n"
                return subprocess.CompletedProcess(argv, 0, stdout=value)

            with patch.object(
                secure_jellyfin_network.subprocess,
                "run",
                side_effect=address_for_interface,
            ):
                secure_jellyfin_network.secure_network_config(path)
            root = ET.parse(path).getroot()

            self.assertEqual(root.tag, "NetworkConfiguration")
            self.assertEqual(
                [item.text for item in root.find("LocalNetworkAddresses")],
                ["127.0.0.1", "192.168.0.111"],
            )
            self.assertEqual(root.findtext("EnableRemoteAccess"), "false")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_global_ipv6_interface_address_is_rejected(self):
        with patch.object(
            secure_jellyfin_network.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, stdout="2001:db8::1\n"),
        ):
            self.assertEqual(
                secure_jellyfin_network.lan_bind_addresses(), ("127.0.0.1",)
            )

    def test_existing_config_preserves_other_settings_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "network.xml"
            path.write_text(
                "<NetworkConfiguration><InternalHttpPort>8123</InternalHttpPort>"
                "<EnableRemoteAccess>true</EnableRemoteAccess>"
                "<LocalNetworkAddresses><string>utun420</string>"
                "</LocalNetworkAddresses></NetworkConfiguration>"
            )
            secure_jellyfin_network.secure_network_config(path)
            first = path.read_bytes()
            secure_jellyfin_network.secure_network_config(path)

            root = ET.parse(path).getroot()
            self.assertEqual(root.findtext("InternalHttpPort"), "8123")
            self.assertEqual(root.findtext("EnableRemoteAccess"), "false")
            self.assertNotIn(b"utun420", first)
            self.assertEqual(path.read_bytes(), first)

    def test_invalid_config_fails_closed_without_rewriting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "network.xml"
            path.write_text("<Unexpected />")
            with self.assertRaises(ValueError):
                secure_jellyfin_network.secure_network_config(path)
            self.assertEqual(path.read_text(), "<Unexpected />")

    def test_disabled_ipv4_fails_closed_without_rewriting(self):
        for setting in ("EnableIPv4", "EnableIPV4"):
            with (
                self.subTest(setting=setting),
                tempfile.TemporaryDirectory() as directory,
            ):
                path = pathlib.Path(directory) / "network.xml"
                original = (
                    f"<NetworkConfiguration><{setting}>false</{setting}>"
                    "<EnableIPv6>true</EnableIPv6></NetworkConfiguration>"
                )
                path.write_text(original)
                with self.assertRaisesRegex(ValueError, f"{setting} must be true"):
                    secure_jellyfin_network.secure_network_config(path)
                self.assertEqual(path.read_text(), original)

    def test_old_config_is_not_shadowed_before_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = pathlib.Path(directory)
            (parent / "system.xml").write_text("<ServerConfiguration />")
            with self.assertRaises(ValueError):
                secure_jellyfin_network.secure_network_config(parent / "network.xml")
            self.assertFalse((parent / "network.xml").exists())

    def test_daemon_applies_network_config_before_exec(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            app = home / "Jellyfin.app/Contents"
            binary = app / "MacOS/jellyfin"
            binary.parent.mkdir(parents=True)
            (app / "Resources/jellyfin-web").mkdir(parents=True)
            (app / "Resources/jellyfin-web/index.html").touch()
            binary.write_text("#!/bin/sh\nprintf 'executed' > \"$HOME/jellyfin-ran\"\n")
            binary.chmod(0o755)
            env = os.environ.copy()
            env["HOME"] = directory
            env["PATH"] = f"{binary.parent}:{env['PATH']}"

            result = subprocess.run(
                ["bash", str(ROOT / "media-streaming/scripts/jellyfin-daemon.sh")],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual((home / "jellyfin-ran").read_text(), "executed")
            path = home / "Library/Application Support/jellyfin/config/network.xml"
            self.assertEqual(
                ET.parse(path).getroot().findtext("EnableRemoteAccess"), "false"
            )
            addresses = ET.parse(path).getroot().find("LocalNetworkAddresses")
            for address in addresses:
                value = ipaddress.IPv4Address(address.text)
                self.assertTrue(
                    value.is_loopback
                    or any(
                        value in network
                        for network in secure_jellyfin_network.PRIVATE_LAN_NETWORKS
                    )
                )

    def test_daemon_refuses_invalid_config_before_exec(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            app = home / "Jellyfin.app/Contents"
            binary = app / "MacOS/jellyfin"
            binary.parent.mkdir(parents=True)
            (app / "Resources/jellyfin-web").mkdir(parents=True)
            (app / "Resources/jellyfin-web/index.html").touch()
            binary.write_text("#!/bin/sh\nprintf 'executed' > \"$HOME/jellyfin-ran\"\n")
            binary.chmod(0o755)
            network_config = (
                home / "Library/Application Support/jellyfin/config/network.xml"
            )
            network_config.parent.mkdir(parents=True)
            network_config.write_text("<Unexpected />")
            env = os.environ.copy()
            env["HOME"] = directory
            env["PATH"] = f"{binary.parent}:{env['PATH']}"

            result = subprocess.run(
                ["bash", str(ROOT / "media-streaming/scripts/jellyfin-daemon.sh")],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertFalse((home / "jellyfin-ran").exists())
            self.assertEqual(network_config.read_text(), "<Unexpected />")


if __name__ == "__main__":
    unittest.main()
