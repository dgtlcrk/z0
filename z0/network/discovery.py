"""Active LAN discovery for z0_n3t."""

from __future__ import annotations

import ipaddress
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from typing import Any

from z0.network.neighbors import collect_neighbors
from z0.network.status import collect_network_status


MAX_WORKERS = 32


@dataclass(frozen=True)
class DiscoveredHost:
    ip_address: str
    mac_address: str
    hostname: str
    interface: str
    state: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _probe(ip_address: str) -> bool:
    result = subprocess.run(
        [
            "ping",
            "-c",
            "1",
            "-W",
            "1",
            ip_address,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode == 0


def _hostname_for_ip(ip_address: str) -> str:
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
    except (OSError, socket.herror):
        return ""

    return hostname


def _candidate_addresses(network: str) -> list[str]:
    try:
        subnet = ipaddress.ip_network(
            network,
            strict=False,
        )
    except ValueError:
        return []

    if subnet.version != 4:
        return []

    return [
        str(address)
        for address in subnet.hosts()
    ]


def discover_hosts() -> list[DiscoveredHost]:
    status = collect_network_status()

    addresses = _candidate_addresses(
        status.network
    )

    if not addresses:
        return []

    workers = min(
        MAX_WORKERS,
        len(addresses),
    )

    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:
        results = list(
            executor.map(
                _probe,
                addresses,
            )
        )

    reachable = [
        address
        for address, is_up in zip(
            addresses,
            results,
            strict=True,
        )
        if is_up
    ]

    neighbors = {
        neighbor.ip_address: neighbor
        for neighbor in collect_neighbors()
    }

    discovered: list[DiscoveredHost] = []

    for ip_address in reachable:
        neighbor = neighbors.get(ip_address)

        mac_address = ""
        interface = status.interface
        source = "icmp"

        if neighbor is not None:
            mac_address = neighbor.mac_address
            interface = neighbor.interface
            source = "icmp+linux_neighbor"

        if ip_address == status.ipv4_address:
            hostname = socket.gethostname()
            source = "icmp+local_host"
        else:
            hostname = _hostname_for_ip(
                ip_address
            )

        discovered.append(
            DiscoveredHost(
                ip_address=ip_address,
                mac_address=mac_address,
                hostname=hostname,
                interface=interface,
                state="ONLINE",
                source=source,
            )
        )

    return sorted(
        discovered,
        key=lambda item: ipaddress.ip_address(
            item.ip_address
        ),
    )
