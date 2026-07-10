#!/usr/bin/env python3
"""Bootstrap local Jellyfin admin + CloudMedia libraries (LAN only).

SECURITY:
- Creates built-in Jellyfin auth only (no SSO).
- Does not open firewall / Windscribe.
- Writes credentials under ~/Library/Application Support/jellyfin with mode 0600.
- Rotate password into 1Password (MediaServer) after first login.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import string
import subprocess  # nosec B404 — used only for fixed launchctl argv (no shell)
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = os.environ.get("JELLYFIN_URL", "http://127.0.0.1:8096").rstrip("/")
MOUNT = Path(os.environ.get("JELLYFIN_MEDIA_ROOT", Path.home() / "CloudMedia/mounted"))
JF_DIR = Path.home() / "Library/Application Support/jellyfin"
CREDS = JF_DIR / "local-admin.credentials"
SYSTEM_XML = JF_DIR / "config" / "system.xml"
CLIENT_HDR = (
    'MediaBrowser Client="Stream3", Device="cursor-agent", '
    'DeviceId="stream3-migrate", Version="1.0.0"'
)


def http(
    method: str,
    path: str,
    *,
    body: dict | None = None,
    token: str | None = None,
    timeout: float = 30.0,
) -> tuple[int, object]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Authorization": CLIENT_HDR},
    )
    if token:
        req.add_header("Authorization", f"MediaBrowser Token={token}")
    # SECURITY: BASE is loopback by default; reject non-http(s) schemes.
    if not BASE.startswith(("http://", "https://")):
        raise ValueError(f"Refusing non-http(s) JELLYFIN_URL: {BASE!r}")
    try:
        with urllib.request.urlopen(
            req, timeout=timeout
        ) as resp:  # nosec B310 — http(s) only via BASE gate
            raw = resp.read()
            code = resp.getcode()
            if not raw:
                return code, None
            try:
                return code, json.loads(raw.decode())
            except json.JSONDecodeError:
                return code, raw.decode(errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload: object = json.loads(raw.decode()) if raw else None
        except json.JSONDecodeError:
            payload = raw.decode(errors="replace") if raw else None
        return e.code, payload


def _launchctl_bin() -> str:
    """Resolve absolute launchctl path (bandit B607)."""
    for candidate in ("/bin/launchctl", "/usr/bin/launchctl"):
        if Path(candidate).is_file():
            return candidate
    found = shutil.which("launchctl")
    if found:
        return found
    raise RuntimeError("launchctl not found")


def public_info() -> dict:
    code, payload = http("GET", "/System/Info/Public")
    if code != 200 or not isinstance(payload, dict):
        raise RuntimeError(f"System/Info/Public failed: {code} {payload}")
    return payload


def load_or_create_creds() -> tuple[str, str]:
    if CREDS.exists():
        user = passwd = ""  # nosec B105 — empty until credential file lines are parsed
        for line in CREDS.read_text().splitlines():
            if line.startswith("JELLYFIN_USER="):
                user = line.split("=", 1)[1]
            elif line.startswith("JELLYFIN_PASSWORD="):
                passwd = line.split("=", 1)[1]
        if user and passwd:
            return user, passwd
    alphabet = string.ascii_letters + string.digits
    user = "speedybee"
    passwd = "".join(secrets.choice(alphabet) for _ in range(28))
    CREDS.parent.mkdir(parents=True, exist_ok=True)
    CREDS.write_text(
        "\n".join(
            [
                "# LOCAL ONLY — do not commit. Rotate into 1Password item MediaServer.",
                f"JELLYFIN_URL={BASE}",
                f"JELLYFIN_USER={user}",
                f"JELLYFIN_PASSWORD={passwd}",
                "",
            ]
        )
    )
    CREDS.chmod(0o600)
    return user, passwd


def reset_wizard_flag() -> None:
    """Allow Startup/User again when wizard was marked complete with zero users."""
    if not SYSTEM_XML.exists():
        return
    text = SYSTEM_XML.read_text()
    if "<IsStartupWizardCompleted>true</IsStartupWizardCompleted>" not in text:
        return
    SYSTEM_XML.write_text(
        text.replace(
            "<IsStartupWizardCompleted>true</IsStartupWizardCompleted>",
            "<IsStartupWizardCompleted>false</IsStartupWizardCompleted>",
        )
    )
    print("Reset IsStartupWizardCompleted=false in system.xml")
    uid = os.getuid()
    plist = Path.home() / "Library/LaunchAgents/com.speedybee.jellyfin.plist"
    # SECURITY: absolute launchctl + constant argv; never shell=True / user input.
    lc = _launchctl_bin()
    label = f"gui/{uid}/com.speedybee.jellyfin"

    def _lc_run(
        args: list[str], *, capture: bool = False
    ) -> subprocess.CompletedProcess[bytes]:
        # nosec B603 — fixed /bin/launchctl argv only
        if capture:
            return subprocess.run(args, capture_output=True)  # nosec B603
        return subprocess.run(args, check=False)  # nosec B603

    _lc_run([lc, "kickstart", "-k", label])
    # If kickstart fails (label not loaded), try bootstrap
    if _lc_run([lc, "print", label], capture=True).returncode != 0:
        _lc_run([lc, "bootstrap", f"gui/{uid}", str(plist)])
        _lc_run([lc, "kickstart", "-k", label])
    for i in range(60):
        try:
            info = public_info()
            print(f"wait restart {i}: wizard={info.get('StartupWizardCompleted')}")
            if info.get("StartupWizardCompleted") is False:
                return
        except Exception as exc:  # noqa: BLE001 — wait loop
            print(f"wait restart {i}: {exc}")
        time.sleep(2)
    raise RuntimeError("Jellyfin did not come back with wizard incomplete")


def ensure_admin(user: str, passwd: str) -> str:
    code, users = http("GET", "/Users/Public")
    if code == 200 and isinstance(users, list) and users:
        print(
            f"Public users already exist: {[u.get('Name') for u in users if isinstance(u, dict)]}"
        )
    else:
        info = public_info()
        if info.get("StartupWizardCompleted") is True:
            reset_wizard_flag()
        print("POST /Startup/Configuration")
        http(
            "POST",
            "/Startup/Configuration",
            body={
                "ServerName": "CloudMedia",
                "UICulture": "en-US",
                "MetadataCountryCode": "US",
                "PreferredMetadataLanguage": "en",
            },
        )
        # Jellyfin 10.11: GET /Startup/User (alias FirstUser) then POST /Startup/User
        # with Name+Password. Empty Password returns 400; FirstUser is GET-only.
        print("GET /Startup/User", http("GET", "/Startup/User"))
        print("POST /Startup/User")
        code, payload = http(
            "POST",
            "/Startup/User",
            body={"Name": user, "Password": passwd},
        )
        if code not in (200, 204):
            raise RuntimeError(
                f"Failed to create admin user: {code} {payload} "
                f"(password_len={len(passwd)})"
            )
        print("POST /Startup/RemoteAccess (LAN only)")
        http(
            "POST",
            "/Startup/RemoteAccess",
            body={"EnableRemoteAccess": False, "EnableAutomaticPortMapping": False},
        )
        print("POST /Startup/Complete")
        http("POST", "/Startup/Complete")

    print("AuthenticateByName")
    code, auth = http(
        "POST",
        "/Users/AuthenticateByName",
        body={"Username": user, "Pw": passwd},
    )
    if code != 200 or not isinstance(auth, dict) or "AccessToken" not in auth:
        raise RuntimeError(f"Auth failed: {code} {auth}")
    token = str(auth["AccessToken"])
    (JF_DIR / "local-api-key.txt").write_text(token + "\n")
    (JF_DIR / "local-api-key.txt").chmod(0o600)
    return token


def ensure_library(token: str, name: str, path: Path, collection_type: str) -> None:
    code, folders = http("GET", "/Library/VirtualFolders", token=token)
    if code != 200 or not isinstance(folders, list):
        raise RuntimeError(f"VirtualFolders list failed: {code} {folders}")
    for folder in folders:
        if not isinstance(folder, dict):
            continue
        if folder.get("Name") == name:
            locs = folder.get("Locations") or []
            print(f"Library already present: {name} -> {locs}")
            return

    qs = urllib.parse.urlencode(
        {
            "name": name,
            "collectionType": collection_type,
            "paths": str(path),
            "refreshLibrary": "true",
        }
    )
    print(f"Add library {name} at {path}")
    code, payload = http(
        "POST",
        f"/Library/VirtualFolders?{qs}",
        body={},
        token=token,
        timeout=120.0,
    )
    if code not in (200, 204):
        raise RuntimeError(f"Add VirtualFolder failed: {code} {payload}")


def wait_for_items(token: str, timeout_s: int = 180) -> int:
    deadline = time.time() + timeout_s
    last = 0
    while time.time() < deadline:
        code, payload = http(
            "GET",
            "/Items?Recursive=true&IncludeItemTypes=Movie,Episode&Limit=5",
            token=token,
            timeout=60.0,
        )
        if code == 200 and isinstance(payload, dict):
            last = int(payload.get("TotalRecordCount") or 0)
            names = [
                i.get("Name")
                for i in (payload.get("Items") or [])[:3]
                if isinstance(i, dict)
            ]
            print(f"Items TotalRecordCount={last} sample={names}")
            if last > 0:
                return last
        else:
            print(f"Items poll -> {code} {payload}")
        # nudge refresh
        http("POST", "/Library/Refresh", token=token)
        time.sleep(5)
    return last


def main() -> int:
    info = public_info()
    print("Public:", json.dumps(info))
    if not MOUNT.is_dir() or not any(MOUNT.iterdir()):
        print(f"ERROR: mount empty/missing: {MOUNT}", file=sys.stderr)
        return 1

    user, passwd = load_or_create_creds()
    token = ensure_admin(user, passwd)
    ensure_library(token, "Movies", MOUNT / "Movies", "movies")
    ensure_library(token, "TV Shows", MOUNT / "TV Shows", "tvshows")
    http("POST", "/Library/Refresh", token=token)
    count = wait_for_items(token)
    print(f"DONE items={count} url={BASE} user={user} creds={CREDS}")
    return 0 if count > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
