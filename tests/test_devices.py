"""Tests for normalized LAN device inventory."""

from z0.network.devices import (
    NetworkDevice,
    _is_ipv4_lan_address,
)


def test_network_device_to_dict() -> None:
    device = NetworkDevice(
        ip_address="192.168.1.10",
        mac_address="aa:bb:cc:dd:ee:ff",
        hostname="test-host",
        interface="wlan0",
        state="REACHABLE",
        source="linux_neighbor",
        role="neighbor",
    )

    result = device.to_dict()

    assert result["ip_address"] == "192.168.1.10"
    assert result["hostname"] == "test-host"
    assert result["source"] == "linux_neighbor"
    assert result["role"] == "neighbor"


def test_ipv4_lan_address_matches_network() -> None:
    assert _is_ipv4_lan_address(
        "192.168.1.20",
        "192.168.1.0/24",
    )


def test_ipv4_lan_address_rejects_docker_network() -> None:
    assert not _is_ipv4_lan_address(
        "172.17.0.3",
        "192.168.1.0/24",
    )


def test_ipv4_lan_address_rejects_ipv6() -> None:
    assert not _is_ipv4_lan_address(
        "fe80::1",
        "192.168.1.0/24",
    )
