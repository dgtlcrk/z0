"""Persistent network device inventory for z0_n3t."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from z0.network.devices import collect_devices

DEFAULT_INVENTORY_PATH = (
    Path.home() / ".config" / "z0" / "network_inventory.json"
)


@dataclass
class InventoryDevice:
    """Persisted network device record."""

    ip_address: str
    mac_address: str
    hostname: str
    role: str
    state: str
    source: str
    first_seen: str
    last_seen: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _device_key(
    ip_address: str,
    mac_address: str,
) -> str:
    """Return the stable inventory key for a device."""

    if mac_address:
        return mac_address.lower()

    return f"ip:{ip_address}"


def load_inventory(
    path: Path = DEFAULT_INVENTORY_PATH,
) -> dict[str, InventoryDevice]:
    """Load persistent network inventory."""

    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}

    inventory: dict[str, InventoryDevice] = {}

    for key, value in data.items():
        try:
            inventory[key] = InventoryDevice(**value)
        except (TypeError, KeyError):
            continue

    return inventory


def save_inventory(
    inventory: dict[str, InventoryDevice],
    path: Path = DEFAULT_INVENTORY_PATH,
) -> None:
    """Write persistent network inventory."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = {
        key: device.to_dict()
        for key, device in sorted(inventory.items())
    }

    path.write_text(
        json.dumps(
            data,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def update_inventory(
    path: Path = DEFAULT_INVENTORY_PATH,
) -> dict[str, InventoryDevice]:
    """Update persistent inventory from current LAN discovery."""

    inventory = load_inventory(path)
    timestamp = _now()

    current_devices = collect_devices()

    current_keys: set[str] = set()

    for device in current_devices:
        key = _device_key(
            device.ip_address,
            device.mac_address,
        )

        current_keys.add(key)

        existing = inventory.get(key)

        if existing is None:
            inventory[key] = InventoryDevice(
                ip_address=device.ip_address,
                mac_address=device.mac_address,
                hostname=device.hostname,
                role=device.role,
                state=device.state,
                source=device.source,
                first_seen=timestamp,
                last_seen=timestamp,
            )
            continue

        existing.ip_address = device.ip_address
        existing.mac_address = device.mac_address

        if device.hostname:
            existing.hostname = device.hostname

        existing.role = device.role
        existing.state = device.state
        existing.source = device.source
        existing.last_seen = timestamp

    for key, device in inventory.items():
        if key not in current_keys:
            device.state = "OFFLINE"

    save_inventory(
        inventory,
        path,
    )

    return inventory


def inventory_devices(
    path: Path = DEFAULT_INVENTORY_PATH,
) -> list[InventoryDevice]:
    """Return inventory records sorted by IPv4 address."""

    inventory = load_inventory(path)

    def sort_key(
        device: InventoryDevice,
    ) -> tuple[int, ...]:
        try:
            return tuple(
                int(part)
                for part in device.ip_address.split(".")
            )
        except ValueError:
            return (999,)

    return sorted(
        inventory.values(),
        key=sort_key,
    )
