"""Normalized LAN device inventory for z0_n3t."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import asdict, dataclass
from typing import Any

from z0.network.discovery import discover_hosts
from z0.network.gateway import collect_gateway_status
from z0.network.neighbors import collect_neighbors
from z0.network.status import collect_network_status


@dataclass(frozen=True)
class NetworkDevice:
    ip_address: str
    mac_address: str
    hostname: str
    interface: str
    state: str
    source: str
    role: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hostname_for_ip(ip_address: str) -> str:
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
    except (OSError, socket.herror):
        return ""

    return hostname


def _is_ipv4_lan_address(
    ip_address: str,
    network: str,
) -> bool:
    try:
        address = ipaddress.ip_address(ip_address)
        subnet = ipaddress.ip_network(
            network,
            strict=False,
        )
    except ValueError:
        return False

    return address.version == 4 and address in subnet


def _merge_sources(*sources: str) -> str:
    result: list[str] = []

    for source in sources:
        for item in source.split("+"):
            if item and item not in result:
                result.append(item)

    return "+".join(result)


def collect_devices() -> list[NetworkDevice]:
    network_status = collect_network_status()
    gateway_status = collect_gateway_status()

    local_ip = network_status.ipv4_address
    gateway_ip = network_status.gateway
    lan_network = network_status.network

    records: dict[str, NetworkDevice] = {}

    for neighbor in collect_neighbors():
        if not _is_ipv4_lan_address(
            neighbor.ip_address,
            lan_network,
        ):
            continue

        # FAILED/INCOMPLETE ARP probes can create neighbor-table
        # entries without a link-layer identity. They are observations
        # of an attempted lookup, not evidence of a real LAN device.
        if not neighbor.mac_address:
            continue

        role = "neighbor"
        source = "linux_neighbor"
        hostname = _hostname_for_ip(
            neighbor.ip_address
        )

        if neighbor.ip_address == gateway_ip:
            role = "gateway"

            if gateway_status.model:
                hostname = gateway_status.model

            source = _merge_sources(
                source,
                "gateway",
            )

        records[neighbor.ip_address] = NetworkDevice(
            ip_address=neighbor.ip_address,
            mac_address=neighbor.mac_address,
            hostname=hostname,
            interface=neighbor.interface,
            state=neighbor.state,
            source=source,
            role=role,
        )

    for host in discover_hosts():
        if not _is_ipv4_lan_address(
            host.ip_address,
            lan_network,
        ):
            continue

        existing = records.get(
            host.ip_address
        )

        mac_address = host.mac_address
        hostname = host.hostname
        interface = host.interface
        source = host.source
        role = "neighbor"

        if existing is not None:
            if not mac_address:
                mac_address = existing.mac_address

            if not hostname:
                hostname = existing.hostname

            if not interface:
                interface = existing.interface

            source = _merge_sources(
                existing.source,
                source,
            )

        if host.ip_address == gateway_ip:
            role = "gateway"

            if gateway_status.model:
                hostname = gateway_status.model

            source = _merge_sources(
                source,
                "gateway",
            )

        if host.ip_address == local_ip:
            role = "local_node"
            hostname = socket.gethostname()
            source = _merge_sources(
                source,
                "local_host",
            )

        records[host.ip_address] = NetworkDevice(
            ip_address=host.ip_address,
            mac_address=mac_address,
            hostname=hostname,
            interface=interface,
            state="ONLINE",
            source=source,
            role=role,
        )

    if local_ip and local_ip not in records:
        records[local_ip] = NetworkDevice(
            ip_address=local_ip,
            mac_address="",
            hostname=socket.gethostname(),
            interface=network_status.interface,
            state="ONLINE",
            source="local_host",
            role="local_node",
        )

    return sorted(
        records.values(),
        key=lambda item: ipaddress.ip_address(
            item.ip_address
        ),
    )
