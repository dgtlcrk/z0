"""Versioned, opt-in persistent inventory of unified network observations.

Legacy network_inventory.json is never read or written by this module.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from z0.network.unified import UnifiedDevice, collect_unified_devices

DEFAULT_PATH = Path.home() / ".config" / "z0" / "unified_inventory_v2.json"
SCHEMA_VERSION = 2


@dataclass
class TrackedDevice:
    mac_address: str
    ip_address: str
    hostname: str
    state: str
    gateway_status: str
    last_activity: str
    connection_type: str
    sources: list[str]
    first_seen: str
    last_observed: str
    last_confirmed_online: str
    observation_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def identity(device: UnifiedDevice) -> str:
    if device.mac_address:
        return device.mac_address.lower()
    if device.ip_address:
        return f"ip:{device.ip_address}"
    raise ValueError("Device lacks both MAC and IP address")


def load_tracked(path: Path = DEFAULT_PATH) -> dict[str, TrackedDevice]:
    if not path.exists():
        return {}
    # Fail closed on corruption, unknown schemas, or invalid records.
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != SCHEMA_VERSION:
        raise ValueError(f"Invalid unified inventory schema: {path}")
    records = payload.get("devices")
    if not isinstance(records, dict):
        raise ValueError(f"Invalid unified inventory records: {path}")
    result: dict[str, TrackedDevice] = {}
    for key, record in records.items():
        if not isinstance(key, str) or not isinstance(record, dict):
            raise ValueError(f"Invalid unified inventory entry: {key}")
        result[key] = TrackedDevice(**record)
    return result


def merge_tracked(
    existing: dict[str, TrackedDevice],
    observed: list[UnifiedDevice],
    *,
    timestamp: str | None = None,
) -> dict[str, TrackedDevice]:
    """Return new snapshot without mutating the supplied inventory."""
    now = timestamp or datetime.now(UTC).isoformat()
    result = {
        key: TrackedDevice(**value.to_dict()) for key, value in existing.items()
    }
    seen: set[str] = set()
    for item in observed:
        key = identity(item)
        if key in seen:
            raise ValueError(f"Duplicate observation identity: {key}")
        seen.add(key)
        previous = result.get(key)
        # Only independently confirmed online observations update this field.
        confirmed = item.state == "ONLINE" and (
            "icmp" in item.sources or "local_host" in item.sources
        )
        if previous is None:
            result[key] = TrackedDevice(
                mac_address=item.mac_address,
                ip_address=item.ip_address,
                hostname=item.hostname,
                state=item.state,
                gateway_status=item.gateway_status,
                last_activity=item.last_activity,
                connection_type=item.connection_type,
                sources=list(item.sources),
                first_seen=now,
                last_observed=now,
                last_confirmed_online=now if confirmed else "",
                observation_count=1,
            )
            continue
        previous.ip_address = item.ip_address or previous.ip_address
        if item.hostname and not item.hostname.lower().startswith("unknown"):
            previous.hostname = item.hostname
        elif not previous.hostname:
            previous.hostname = item.hostname
        previous.mac_address = item.mac_address or previous.mac_address
        previous.state = item.state
        previous.gateway_status = item.gateway_status
        previous.last_activity = item.last_activity
        previous.connection_type = item.connection_type
        previous.sources = list(item.sources)
        previous.last_observed = now
        if confirmed:
            previous.last_confirmed_online = now
        previous.observation_count += 1
    # Missing an observation is not evidence that the device is offline.
    for key, item in result.items():
        if key not in seen:
            item.state = "NOT_OBSERVED"
    return result


def save_tracked(
    records: dict[str, TrackedDevice], path: Path = DEFAULT_PATH
) -> None:
    """Atomically replace a dedicated version-2 file after serialization."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": SCHEMA_VERSION,
        "devices": {
            key: value.to_dict() for key, value in sorted(records.items())
        },
    }
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", delete=False,
        ) as handle:
            name = handle.name
            os.chmod(name, 0o600)
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if name is not None and os.path.exists(name):
            os.unlink(name)


def update_tracked(path: Path = DEFAULT_PATH) -> dict[str, TrackedDevice]:
    # Load before scanning so corrupt files cannot be accidentally overwritten.
    existing = load_tracked(path)
    observed = collect_unified_devices()
    updated = merge_tracked(existing, observed)
    save_tracked(updated, path)
    return updated
