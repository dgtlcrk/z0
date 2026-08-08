"""Tests for Linux-native network edge status."""

from z0.network.status import (
    NetworkStatus,
    collect_network_status,
)


def test_network_status_to_dict() -> None:
    status = NetworkStatus(
        interface="wlan0",
        ipv4_address="192.168.1.191",
        network="192.168.1.0/24",
        gateway="192.168.1.254",
        gateway_reachable=True,
        dns_server="192.168.1.254",
        dns_working=True,
        ipv4_internet=True,
        ipv6_available=True,
    )

    result = status.to_dict()

    assert result["interface"] == "wlan0"
    assert result["network"] == "192.168.1.0/24"
    assert result["gateway"] == "192.168.1.254"
    assert result["gateway_reachable"] is True


def test_collect_network_status_returns_status() -> None:
    result = collect_network_status()

    assert isinstance(result, NetworkStatus)
    assert isinstance(result.interface, str)
    assert isinstance(result.gateway, str)
