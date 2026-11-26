"""Tests for media-streaming/scripts/backup-jellyfin.py."""

import importlib.util
import os
import sqlite3
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "media-streaming" / "scripts" / "backup-jellyfin.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("backup_jellyfin", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestBackupJellyfin(unittest.TestCase):
    """Unit and round-trip integration tests for encrypted Jellyfin backups."""

    def setUp(self) -> None:
        prev_umask = os.umask(0o022)
        self.addCleanup(os.umask, prev_umask)

    def _setup_wal_fixture(
        self, root: Path
    ) -> tuple[Path, Path, Path, Path, sqlite3.Connection]:
        home = root / "home"
        server = home / "Library/Application Support/jellyfin"
        keys = server.parent / "CloudMedia Recovery"
        drive = (
            home
            / "Library/CloudStorage/GoogleDrive-test@example.com/My Drive/HomeBackup"
        )
        for rel in ("data/playlists", "config", "plugins", "root"):
            (server / rel).mkdir(parents=True)
        drive.mkdir(parents=True)
        keys.mkdir(mode=0o755, parents=True)
        os.chmod(keys, 0o755)
        self.assertEqual(stat.S_IMODE(keys.stat().st_mode), 0o755)
        (server / "config/system.xml").write_text("<System />", encoding="utf-8")
        (server / "data/playlists/list.xml").write_text("<P />", encoding="utf-8")
        (server / "data/device.txt").write_text("device-1", encoding="utf-8")
        conn = sqlite3.connect(server / "data/jellyfin.db")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO items (name) VALUES ('movie-1')")
        conn.commit()
        conn.execute("INSERT INTO items (name) VALUES ('movie-2')")
        conn.commit()
        return home, server, keys, drive, conn

    def _fake_openssl_runner(self) -> Any:
        def fake_run(*args: str) -> None:
            if args[0] == "req":
                Path(args[args.index("-keyout") + 1]).write_bytes(b"KEYDATA")
                Path(args[args.index("-out") + 1]).write_bytes(b"CERTDATA")
            elif args[0] == "cms":
                in_file = Path(args[args.index("-in") + 1])
                out_file = Path(args[args.index("-out") + 1])
                if "-encrypt" in args:
                    out_file.write_bytes(b"CMS:" + in_file.read_bytes())
                elif "-decrypt" in args:
                    payload = in_file.read_bytes()
                    self.assertTrue(payload.startswith(b"CMS:"))
                    out_file.write_bytes(payload[4:])

        return fake_run

    def test_snapshot_build_archive_and_publish_with_wal_db(self) -> None:
        mod = _load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home, server, keys, drive, conn = self._setup_wal_fixture(root)
            try:
                with mock.patch.object(mod, "HOME", home), mock.patch.object(
                    mod, "SERVER", server
                ), mock.patch.object(mod, "KEYS", keys), mock.patch.object(
                    mod, "run", side_effect=self._fake_openssl_runner()
                ):
                    mod.main()
            finally:
                conn.close()

            self.assertEqual(stat.S_IMODE(keys.stat().st_mode), 0o700)
            local_snaps = list((keys / "snapshots").glob("jellyfin-*.cms"))
            drive_snaps = list((drive / "CloudMedia Recovery").glob("jellyfin-*.cms"))
            self.assertEqual(len(local_snaps), 1)
            self.assertEqual(len(drive_snaps), 1)

            extracted_zip = root / "out.zip"
            extracted_zip.write_bytes(local_snaps[0].read_bytes()[4:])
            with zipfile.ZipFile(extracted_zip) as zf:
                names = set(zf.namelist())
                self.assertIn("data/jellyfin.db", names)
                self.assertIn("config/system.xml", names)
                self.assertIn("data/device.txt", names)
                zf.extract("data/jellyfin.db", root / "restored")

            rconn = sqlite3.connect(root / "restored/data/jellyfin.db")
            try:
                rows = rconn.execute("SELECT name FROM items ORDER BY id").fetchall()
                self.assertEqual(rows, [("movie-1",), ("movie-2",)])
            finally:
                rconn.close()

    def test_ensure_keypair_fails_closed_when_half_missing(self) -> None:
        mod = _load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            work = root / "work"
            work.mkdir()
            key = root / "recovery.pem"
            cert = root / "recipient.crt"
            key.write_text("only-key", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Incomplete recovery keypair"):
                mod._ensure_keypair(work, key, cert)

    def test_main_skips_cleanly_when_lock_contended(self) -> None:
        mod = _load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            keys = Path(tmpdir) / "CloudMedia Recovery"
            with mock.patch.object(mod, "KEYS", keys), mock.patch.object(
                mod.fcntl, "flock", side_effect=BlockingIOError("locked")
            ), mock.patch.object(mod, "_snapshot_database") as snap_mock:
                mod.main()
                snap_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
