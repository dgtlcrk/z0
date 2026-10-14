"""Read-only optional friendly labels for the browser inventory.

A separate operator-owned JSON file maps MAC addresses to human labels.
No writes to inventory or labels happen in the web/API code.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

DEFAULT_LABELS_PATH = Path.home() / ".config" / "z0" / "device_labels.json"
_MAC = re.compile(r"^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$", re.I)


def load_device_labels(path: Path = DEFAULT_LABELS_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Device labels must be a JSON object")
    result: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not _MAC.fullmatch(key):
            raise ValueError(f"Invalid device label MAC: {key}")
        if not isinstance(value, str) or not (1 <= len(value.strip()) <= 80):
            raise ValueError(f"Invalid friendly label for {key}")
        result[key.lower()] = value.strip()
    return result


def is_generic_hostname(hostname: str) -> bool:
    """Treat collector placeholders as unidentified, not named assets."""
    name = hostname.strip().lower()
    return not name or name.startswith("unknown")


def identification(device: dict[str, object], labels: dict[str, str]) -> dict[str, object]:
    """Derive an honest display identity without altering observed data."""
    mac = str(device.get("mac_address") or "").lower()
    ip = str(device.get("ip_address") or "")
    hostname = str(device.get("hostname") or "").strip()
    if mac in labels:
        display = labels[mac]
        source = "operator_label"
    elif not is_generic_hostname(hostname):
        display = hostname
        source = "observed_hostname"
    else:
        display = f"Unidentified ({ip or mac or 'no address'})"
        source = "unidentified"
    # A locally administered MAC is not proof of a randomized address.
    octet = mac.split(":", 1)[0]
    local_mac = bool(_MAC.fullmatch(mac) and int(octet, 16) & 2)
    return {
        "display_name": display,
        "identification_source": source,
        "locally_administered_mac": local_mac,
    }


def label_devices(
    devices: list[dict[str, object]],
    labels: dict[str, str],
) -> list[dict[str, object]]:
    result = []
    for device in devices:
        updated = dict(device)
        updated.update(identification(device, labels))
        result.append(updated)
    return result
