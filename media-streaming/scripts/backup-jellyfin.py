"""Back up native Jellyfin without stopping a live SQLite library scan."""

import fcntl
import hashlib
import os
import shutil
import sqlite3
import subprocess  # nosec B404 — used only for fixed /opt/homebrew/bin/openssl argv (no shell)
import tempfile
import zipfile
from contextlib import closing
from datetime import date
from pathlib import Path

HOME = Path.home()
SERVER = HOME / "Library/Application Support/jellyfin"
KEYS = SERVER.parent / "CloudMedia Recovery"
SSL = "/opt/homebrew/bin/openssl"


def run(*args):
    subprocess.run([SSL, *args], check=True, timeout=300)  # nosec B603


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").digest()


def publish(src, directory, name):
    directory.mkdir(exist_ok=True, parents=True)
    with tempfile.NamedTemporaryFile(dir=directory, delete=False) as out:
        tmp = Path(out.name)
    try:
        shutil.copyfile(src, tmp)
        if digest(src) != digest(tmp):
            raise RuntimeError("Staged copy failed readback")
        tmp.replace(directory / name)
    finally:
        tmp.unlink(missing_ok=True)


def main():
    os.umask(0o077)
    KEYS.mkdir(mode=0o700, exist_ok=True)
    with (KEYS / "backup.lock").open("a") as lock, tempfile.TemporaryDirectory() as tmp:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        work = Path(tmp)
        key, cert = KEYS / "recovery.pem", KEYS / "recipient.crt"
        if not key.exists() and not cert.exists():
            run(
                "req",
                "-x509",
                "-newkey",
                "rsa:3072",
                "-nodes",
                "-days",
                "3650",
                "-subj",
                "/CN=CloudMedia local recovery",
                "-keyout",
                str(work / "key"),
                "-out",
                str(work / "cert"),
            )
            shutil.copyfile(work / "key", key)
            shutil.copyfile(work / "cert", cert)
        elif key.exists() != cert.exists():
            raise RuntimeError(
                "Incomplete recovery keypair: expected both recovery.pem and recipient.crt"
            )
        db = work / "jellyfin.db"
        source = SERVER / "data/jellyfin.db"
        with closing(
            sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)
        ) as live, closing(sqlite3.connect(db)) as copy:
            live.backup(copy, pages=256)
            if copy.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise RuntimeError("SQLite integrity check failed")
            if not copy.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1"
            ).fetchone():
                raise RuntimeError("Database has no tables")
        archive = work / "snapshot.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=3) as z:
            z.write(db, "data/jellyfin.db")
            for dirname in ("config", "plugins", "root", "data/playlists"):
                for folder, _, files in os.walk(SERVER / dirname):
                    for name in files:
                        p = Path(folder) / name
                        if p.is_file() and not p.is_symlink():
                            z.write(p, p.relative_to(SERVER))
            for name in ("data/device.txt", "library-paths.txt"):
                if (SERVER / name).is_file():
                    z.write(SERVER / name, name)
        with zipfile.ZipFile(archive) as z:
            if z.testzip() or "config/system.xml" not in z.namelist():
                raise RuntimeError("Invalid configuration archive")
        enc = work / "encrypted.cms"
        run(
            "cms",
            "-encrypt",
            "-binary",
            "-aes-256-gcm",
            "-outform",
            "DER",
            "-in",
            str(archive),
            "-out",
            str(enc),
            str(cert),
        )
        restored = work / "restored.zip"
        run(
            "cms",
            "-decrypt",
            "-binary",
            "-inform",
            "DER",
            "-in",
            str(enc),
            "-inkey",
            str(key),
            "-out",
            str(restored),
        )
        if digest(restored) != digest(archive):
            raise RuntimeError("Decryption test failed")
        name = "jellyfin-" + str(date.today().isoweekday()) + ".cms"
        publish(enc, KEYS / "snapshots", name)
        print("Local encrypted backup verified:", name, flush=True)
        roots = list(
            (HOME / "Library/CloudStorage").glob("GoogleDrive-*/My Drive/HomeBackup")
        )
        if len(roots) != 1 or not roots[0].is_dir():
            raise RuntimeError(
                "Expected one existing Google Drive HomeBackup destination"
            )
        publish(enc, roots[0] / "CloudMedia Recovery", name)
        print("Drive File Provider copy verified:", name, flush=True)


if __name__ == "__main__":
    main()
