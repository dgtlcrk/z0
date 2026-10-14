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


def label_devices(
    devices: list[dict[str, object]],
    labels: dict[str, str],
) -> list[dict[str, object]]:
    result = []
    for device in devices:
        updated = dict(device)
        mac = str(device.get("mac_address", "")).lower()
        updated["display_name"] = labels.get(mac) or device.get("hostname") or (
            device.get("ip_address") or mac or "Unidentified device"
        )
        result.append(updated)
    return result
