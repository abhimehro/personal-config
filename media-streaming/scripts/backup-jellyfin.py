"""Back up native Jellyfin without stopping a live SQLite library scan."""

import fcntl
import hashlib
import logging
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
ARCHIVE_DIRS = ("config", "plugins", "root", "data/playlists")
ARCHIVE_FILES = ("data/device.txt", "library-paths.txt")

logger = logging.getLogger(__name__)


def run(*args: str) -> None:
    """Execute OpenSSL with fixed binary path and bounded timeout."""
    subprocess.run([SSL, *args], check=True, timeout=300)  # nosec B603


def digest(path: Path) -> bytes:
    """Return the SHA-256 digest bytes for a file."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").digest()


def publish(src: Path, directory: Path, name: str) -> None:
    """Atomically stage and verify a backup archive copy before publishing."""
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


def _ensure_keypair(work: Path, key: Path, cert: Path) -> None:
    """Ensure both recovery key and certificate exist, or fail closed."""
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
        return
    if key.exists() != cert.exists():
        raise RuntimeError(
            "Incomplete recovery keypair: expected both recovery.pem and recipient.crt"
        )


def _snapshot_database(source: Path, db: Path) -> None:
    """Create and integrity-check a read-only online SQLite backup."""
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


def _add_directory_files(archive: zipfile.ZipFile, dirname: str) -> None:
    """Add regular non-symlink files from a Jellyfin server subdirectory."""
    for folder, _, files in os.walk(SERVER / dirname):
        for name in files:
            candidate = Path(folder) / name
            if candidate.is_file() and not candidate.is_symlink():
                archive.write(candidate, candidate.relative_to(SERVER))


def _build_archive(archive: Path, db: Path) -> None:
    """Package the SQLite snapshot and Jellyfin configuration into a verified zip."""
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=3) as zf:
        zf.write(db, "data/jellyfin.db")
        for dirname in ARCHIVE_DIRS:
            _add_directory_files(zf, dirname)
        for rel_path in ARCHIVE_FILES:
            candidate = SERVER / rel_path
            if candidate.is_file() and not candidate.is_symlink():
                zf.write(candidate, rel_path)
    with zipfile.ZipFile(archive) as zf:
        if zf.testzip() or "config/system.xml" not in zf.namelist():
            raise RuntimeError("Invalid configuration archive")


def _encrypt_and_verify(archive: Path, work: Path, cert: Path, key: Path) -> Path:
    """Encrypt archive via CMS AES-256-GCM and verify round-trip decryption."""
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
    return enc


def _publish_archives(enc: Path, name: str) -> None:
    """Publish verified encrypted archive locally and to Google Drive HomeBackup."""
    publish(enc, KEYS / "snapshots", name)
    logger.info("Local encrypted backup verified: %s", name)
    roots = list(
        (HOME / "Library/CloudStorage").glob("GoogleDrive-*/My Drive/HomeBackup")
    )
    if len(roots) != 1 or not roots[0].is_dir():
        raise RuntimeError("Expected one existing Google Drive HomeBackup destination")
    publish(enc, roots[0] / "CloudMedia Recovery", name)
    logger.info("Drive File Provider copy verified: %s", name)


def main() -> None:
    """Acquire non-blocking lock, snapshot Jellyfin state, encrypt, and publish."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    os.umask(0o077)
    KEYS.mkdir(mode=0o700, exist_ok=True)
    os.chmod(KEYS, 0o700)
    with (KEYS / "backup.lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.info(
                "Another Jellyfin backup instance holds the lock; skipping run."
            )
            return
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            key, cert = KEYS / "recovery.pem", KEYS / "recipient.crt"
            _ensure_keypair(work, key, cert)
            db = work / "jellyfin.db"
            _snapshot_database(SERVER / "data/jellyfin.db", db)
            archive = work / "snapshot.zip"
            _build_archive(archive, db)
            enc = _encrypt_and_verify(archive, work, cert, key)
            name = f"jellyfin-{date.today().isoweekday()}.cms"
            _publish_archives(enc, name)


if __name__ == "__main__":
    main()
