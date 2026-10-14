"""Opt-in manual ICMP availability checks for explicitly selected IPv4 hosts.

Keeps separate, versioned probe history. Does not update device inventory,
schedule checks, or send notifications.
"""

from __future__ import annotations

import ipaddress
import json
import os
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_PATH = Path.home() / ".config" / "z0" / "availability_v1.json"
SCHEMA_VERSION = 1


@dataclass
class HostAvailability:
    address: str
    state: str = "UNCONFIRMED"
    successes: int = 0
    failures: int = 0
    last_checked: str = ""
    last_success: str = ""
    last_failure: str = ""
    last_transition: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AvailabilityEvent:
    address: str
    timestamp: str
    old_state: str
    new_state: str
    result: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def load_events(path: Path = DEFAULT_PATH) -> list[AvailabilityEvent]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != SCHEMA_VERSION:
        raise ValueError("Unsupported availability schema")
    if not isinstance(data.get("hosts"), dict):
        raise ValueError("Invalid availability records")
    raw = data.get("events", [])
    if not isinstance(raw, list):
        raise ValueError("Invalid availability events")
    return [AvailabilityEvent(**event) for event in raw]


def normalize_targets(addresses: list[str]) -> list[str]:
    """Reject anything other than explicit unicast IPv4 addresses."""
    if not addresses:
        raise ValueError("Supply at least one --ip address")
    if len(addresses) > 16:
        raise ValueError("Maximum 16 targets per manual check")
    result: list[str] = []
    for raw in addresses:
        addr = ipaddress.IPv4Address(raw)
        if (
            not addr.is_private or addr.is_multicast or addr.is_unspecified
            or addr.is_loopback or addr.is_link_local
        ):
            raise ValueError(f"Target must be a private LAN IPv4 address: {raw}")
        value = str(addr)
        if value not in result:
            result.append(value)
    return result


def load_availability(path: Path = DEFAULT_PATH) -> dict[str, HostAvailability]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported availability schema: {path}")
    entries = payload.get("hosts")
    if not isinstance(entries, dict):
        raise ValueError(f"Invalid availability records: {path}")
    result = {}
    for address, data in entries.items():
        if not isinstance(data, dict) or not isinstance(address, str):
            raise ValueError(f"Invalid availability host: {address}")
        entry = HostAvailability(**data)
        if entry.address != address:
            raise ValueError(f"Mismatched availability host: {address}")
        result[address] = entry
    return result


def transition(
    previous: HostAvailability, success: bool, *,
    timestamp: str, failure_threshold: int = 3, recovery_threshold: int = 2,
) -> HostAvailability:
    if failure_threshold < 1 or recovery_threshold < 1:
        raise ValueError("Probe thresholds must be positive")
    item = HostAvailability(**previous.to_dict())
    item.last_checked = timestamp
    if success:
        item.successes += 1
        item.failures = 0
        item.last_success = timestamp
        if item.successes >= recovery_threshold and item.state != "AVAILABLE":
            item.state = "AVAILABLE"
            item.last_transition = timestamp
        elif item.state != "AVAILABLE" and item.state != "UNAVAILABLE":
            item.state = "UNCONFIRMED"
    else:
        item.failures += 1
        item.successes = 0
        item.last_failure = timestamp
        if item.failures >= failure_threshold and item.state != "UNAVAILABLE":
            item.state = "UNAVAILABLE"
            item.last_transition = timestamp
        elif item.state != "UNAVAILABLE" and item.state != "AVAILABLE":
            item.state = "UNCONFIRMED"
    return item


def probe_once(address: str) -> bool:
    """One bounded ICMP attempt. Missing ping is an error, not a failed probe."""
    result = subprocess.run(
        ["ping", "-n", "-c", "1", "-W", "1", address],
        capture_output=True, text=True, check=False, timeout=4,
    )
    return result.returncode == 0


def save_availability(
    hosts: dict[str, HostAvailability], path: Path = DEFAULT_PATH,
    *, events: list[AvailabilityEvent] | None = None,
) -> None:
    if events is None:
        events = load_events(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(
        {"version": SCHEMA_VERSION, "hosts": {
            key: value.to_dict() for key, value in sorted(hosts.items())
        }, "events": [event.to_dict() for event in events]},
        indent=2, sort_keys=True,
    ) + "\n"
    name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", delete=False,
        ) as handle:
            name = handle.name
            os.chmod(name, 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def check_targets(
    addresses: list[str], *, path: Path = DEFAULT_PATH,
    failure_threshold: int = 3, recovery_threshold: int = 2,
) -> list[HostAvailability]:
    """Manually check explicit targets; write only after ALL probes succeed."""
    targets = normalize_targets(addresses)
    if failure_threshold < 1 or recovery_threshold < 1:
        raise ValueError("Probe thresholds must be positive")
    hosts = load_availability(path)
    events = load_events(path)
    # Probe every target first so a subprocess failure cannot partially persist.
    outcomes = {address: probe_once(address) for address in targets}
    timestamp = datetime.now(UTC).isoformat()
    for address, success in outcomes.items():
        previous = hosts.get(address, HostAvailability(address=address))
        updated = transition(
            previous, success, timestamp=timestamp,
            failure_threshold=failure_threshold,
            recovery_threshold=recovery_threshold,
        )
        hosts[address] = updated
        if updated.state != previous.state:
            events.append(AvailabilityEvent(
                address=address, timestamp=timestamp,
                old_state=previous.state, new_state=updated.state,
                result="SUCCESS" if success else "FAILURE",
            ))
    save_availability(hosts, path, events=events)
    return [hosts[address] for address in targets]
