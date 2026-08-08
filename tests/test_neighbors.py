"""Tests for Linux neighbor discovery."""

from z0.network.neighbors import (
    Neighbor,
    _parse_neighbor,
)


def test_neighbor_to_dict() -> None:
    neighbor = Neighbor(
        ip_address="192.168.1.10",
        mac_address="aa:bb:cc:dd:ee:ff",
        interface="wlan0",
        state="REACHABLE",
    )

    result = neighbor.to_dict()

    assert result["ip_address"] == "192.168.1.10"
    assert result["mac_address"] == "aa:bb:cc:dd:ee:ff"
    assert result["interface"] == "wlan0"
    assert result["state"] == "REACHABLE"


def test_parse_neighbor() -> None:
    neighbor = _parse_neighbor(
        "192.168.1.10 dev wlan0 "
        "lladdr aa:bb:cc:dd:ee:ff REACHABLE"
    )

    assert neighbor is not None
    assert neighbor.ip_address == "192.168.1.10"
    assert neighbor.mac_address == "aa:bb:cc:dd:ee:ff"
    assert neighbor.interface == "wlan0"
    assert neighbor.state == "REACHABLE"


def test_parse_incomplete_neighbor() -> None:
    neighbor = _parse_neighbor(
        "192.168.1.20 dev wlan0 FAILED"
    )

    assert neighbor is not None
    assert neighbor.ip_address == "192.168.1.20"
    assert neighbor.mac_address == ""
    assert neighbor.interface == "wlan0"
    assert neighbor.state == "FAILED"
