"""Tests for active LAN discovery."""

from z0.network.discovery import (
    DiscoveredHost,
    _candidate_addresses,
)


def test_discovered_host_to_dict() -> None:
    host = DiscoveredHost(
        ip_address="192.168.1.10",
        mac_address="aa:bb:cc:dd:ee:ff",
        hostname="example",
        interface="wlan0",
        state="ONLINE",
        source="icmp+linux_neighbor",
    )

    result = host.to_dict()

    assert result["ip_address"] == "192.168.1.10"
    assert result["mac_address"] == "aa:bb:cc:dd:ee:ff"
    assert result["hostname"] == "example"
    assert result["state"] == "ONLINE"


def test_candidate_addresses_ipv4() -> None:
    result = _candidate_addresses(
        "192.168.50.0/30"
    )

    assert result == [
        "192.168.50.1",
        "192.168.50.2",
    ]


def test_candidate_addresses_rejects_invalid_network() -> None:
    assert _candidate_addresses(
        "not-a-network"
    ) == []


def test_candidate_addresses_rejects_ipv6() -> None:
    assert _candidate_addresses(
        "2001:db8::/126"
    ) == []
