"""Tests for persistent network inventory."""

from pathlib import Path

from z0.network.inventory import (
    InventoryDevice,
    _device_key,
    load_inventory,
    save_inventory,
)


def test_inventory_device_to_dict() -> None:
    device = InventoryDevice(
        ip_address="192.168.1.10",
        mac_address="aa:bb:cc:dd:ee:ff",
        hostname="test-host",
        role="neighbor",
        state="ONLINE",
        source="icmp",
        first_seen="2026-08-08T00:00:00+00:00",
        last_seen="2026-08-08T00:05:00+00:00",
    )

    result = device.to_dict()

    assert result["ip_address"] == "192.168.1.10"
    assert result["hostname"] == "test-host"
    assert result["first_seen"] == "2026-08-08T00:00:00+00:00"
    assert result["last_seen"] == "2026-08-08T00:05:00+00:00"


def test_device_key_prefers_mac() -> None:
    assert _device_key(
        "192.168.1.10",
        "AA:BB:CC:DD:EE:FF",
    ) == "aa:bb:cc:dd:ee:ff"


def test_device_key_falls_back_to_ip() -> None:
    assert _device_key(
        "192.168.1.10",
        "",
    ) == "ip:192.168.1.10"


def test_inventory_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "inventory.json"

    inventory = {
        "aa:bb:cc:dd:ee:ff": InventoryDevice(
            ip_address="192.168.1.10",
            mac_address="aa:bb:cc:dd:ee:ff",
            hostname="test-host",
            role="neighbor",
            state="ONLINE",
            source="icmp",
            first_seen="2026-08-08T00:00:00+00:00",
            last_seen="2026-08-08T00:05:00+00:00",
        )
    }

    save_inventory(
        inventory,
        path,
    )

    loaded = load_inventory(path)

    assert len(loaded) == 1
    assert loaded["aa:bb:cc:dd:ee:ff"].hostname == "test-host"
