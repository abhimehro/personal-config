"""Keep native Jellyfin's HTTP listener off the public VPN interface."""

from __future__ import annotations

import ipaddress
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# en5 is the primary LAN interface on this Mac; en0 is its secondary Wi-Fi.
# Resolve them before writing Jellyfin's config: an interface name alone could
# select a public or IPv6 address when its network changes.
LAN_INTERFACES = ("en5", "en0")
PRIVATE_LAN_NETWORKS = tuple(
    ipaddress.IPv4Network(cidr)
    for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


def lan_bind_addresses() -> tuple[str, ...]:
    addresses = ["127.0.0.1"]
    for interface in LAN_INTERFACES:
        try:
            result = subprocess.run(
                ["/usr/sbin/ipconfig", "getifaddr", interface],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode != 0:
            continue
        try:
            address = ipaddress.IPv4Address(result.stdout.strip())
        except ipaddress.AddressValueError:
            continue
        if any(address in network for network in PRIVATE_LAN_NETWORKS):
            value = str(address)
            if value not in addresses:
                addresses.append(value)
    return tuple(addresses)


def secure_network_config(path: Path) -> None:
    if path.exists():
        tree = ET.parse(path)
        root = tree.getroot()
        if root.tag != "NetworkConfiguration":
            raise ValueError(f"unexpected Jellyfin network config root: {root.tag}")
    else:
        # An old installation may still need Jellyfin's system.xml migration.
        # Do not create a partial network.xml that would skip that migration.
        if (path.parent / "system.xml").exists():
            raise ValueError(
                "network.xml missing while system.xml exists; migrate Jellyfin first"
            )
        root = ET.Element("NetworkConfiguration")
        tree = ET.ElementTree(root)

    for setting in ("EnableIPv4", "EnableIPV4"):
        ipv4 = root.find(setting)
        if ipv4 is not None and (ipv4.text or "").strip().lower() != "true":
            raise ValueError(
                f"{setting} must be true for the restricted HTTP bind addresses"
            )

    safe_addresses = lan_bind_addresses()
    addresses = root.find("LocalNetworkAddresses")
    existing = () if addresses is None else tuple(child.text for child in addresses)
    remote = root.find("EnableRemoteAccess")
    if existing == safe_addresses and remote is not None and remote.text == "false":
        return

    if addresses is None:
        addresses = ET.SubElement(root, "LocalNetworkAddresses")
    addresses.clear()
    for address in safe_addresses:
        ET.SubElement(addresses, "string").text = address
    if remote is None:
        remote = ET.SubElement(root, "EnableRemoteAccess")
    remote.text = "false"

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".network.", suffix=".xml", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            tree.write(stream, encoding="utf-8", xml_declaration=True)
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


if __name__ == "__main__":
    try:
        secure_network_config(Path(sys.argv[1]))
    except (OSError, ValueError, ET.ParseError) as exc:
        print(f"Jellyfin network configuration rejected: {exc}", file=sys.stderr)
        sys.exit(1)
