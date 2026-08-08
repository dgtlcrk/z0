"""Linux-native network edge status collection."""

from __future__ import annotations

import ipaddress
import socket
import subprocess
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class NetworkStatus:
    interface: str
    ipv4_address: str
    network: str
    gateway: str
    gateway_reachable: bool
    dns_server: str
    dns_working: bool
    ipv4_internet: bool
    ipv6_available: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run(*args: str) -> str:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def _ping(host: str) -> bool:
    if not host:
        return False

    result = subprocess.run(
        ["ping", "-c", "1", "-W", "2", host],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _default_route() -> tuple[str, str, str]:
    parts = _run(
        "ip",
        "route",
        "show",
        "default",
    ).split()

    if not parts:
        return "", "", ""

    gateway = parts[parts.index("via") + 1] if "via" in parts else ""
    interface = parts[parts.index("dev") + 1] if "dev" in parts else ""
    source = parts[parts.index("src") + 1] if "src" in parts else ""

    return gateway, interface, source


def _network(interface: str) -> str:
    if not interface:
        return ""

    output = _run(
        "ip",
        "-o",
        "-4",
        "addr",
        "show",
        "dev",
        interface,
    )

    for line in output.splitlines():
        parts = line.split()

        if "inet" in parts:
            address = parts[parts.index("inet") + 1]
            return str(
                ipaddress.ip_interface(address).network
            )

    return ""


def _dns_server() -> str:
    output = _run("resolvectl", "dns")

    for line in output.splitlines():
        if ":" not in line:
            continue

        for value in line.split(":", 1)[1].split():
            try:
                ipaddress.ip_address(value)
            except ValueError:
                continue

            return value

    return ""


def _dns_working() -> bool:
    try:
        socket.getaddrinfo("github.com", 443)
    except OSError:
        return False

    return True


def collect_network_status() -> NetworkStatus:
    gateway, interface, source = _default_route()

    return NetworkStatus(
        interface=interface,
        ipv4_address=source,
        network=_network(interface),
        gateway=gateway,
        gateway_reachable=_ping(gateway),
        dns_server=_dns_server(),
        dns_working=_dns_working(),
        ipv4_internet=_ping("1.1.1.1"),
        ipv6_available=bool(
            _run(
                "ip",
                "-6",
                "route",
                "show",
                "default",
            )
        ),
    )
