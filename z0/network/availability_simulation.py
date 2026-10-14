"""Offline-only availability simulation with persistent transition history.

No network probes. Separate file and schema from real availability history.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from z0.network.availability import HostAvailability, normalize_targets, transition

DEFAULT_SIMULATION_PATH = Path.home() / ".config" / "z0" / "availability_simulation_v1.json"
SIMULATION_SCHEMA = 1


@dataclass(frozen=True)
class TransitionEvent:
    address: str
    timestamp: str
    old_state: str
    new_state: str
    result: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def load_simulation(
    path: Path = DEFAULT_SIMULATION_PATH,
) -> tuple[dict[str, HostAvailability], list[TransitionEvent]]:
    if not path.exists():
        return {}, []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != SIMULATION_SCHEMA:
        raise ValueError("Unsupported simulation schema")
    raw_hosts, raw_events = data.get("hosts"), data.get("events")
    if not isinstance(raw_hosts, dict) or not isinstance(raw_events, list):
        raise ValueError("Invalid simulation records")
    hosts = {key: HostAvailability(**value) for key, value in raw_hosts.items()}
    if any(host.address != key for key, host in hosts.items()):
        raise ValueError("Simulation identity mismatch")
    events = [TransitionEvent(**value) for value in raw_events]
    return hosts, events


def save_simulation(
    hosts: dict[str, HostAvailability],
    events: list[TransitionEvent],
    path: Path = DEFAULT_SIMULATION_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": SIMULATION_SCHEMA,
        "hosts": {key: host.to_dict() for key, host in sorted(hosts.items())},
        "events": [item.to_dict() for item in events],
    }
    serialized = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=f".{path.name}.",
            dir=path.parent, delete=False,
        ) as handle:
            name = handle.name
            os.chmod(name, 0o600)
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def simulate(
    address: str,
    sequence: str,
    *,
    path: Path = DEFAULT_SIMULATION_PATH,
    failure_threshold: int = 3,
    recovery_threshold: int = 2,
) -> tuple[HostAvailability, list[TransitionEvent]]:
    """Apply S(success)/F(failure) sequence without running ICMP."""
    targets = normalize_targets([address])
    if not sequence or len(sequence) > 100:
        raise ValueError("Sequence must contain 1 to 100 S/F outcomes")
    sequence = sequence.upper()
    if set(sequence) - {"S", "F"}:
        raise ValueError("Sequence may contain only S (success) and F (failure)")
    if failure_threshold < 1 or recovery_threshold < 1:
        raise ValueError("Thresholds must be positive")

    # Don't allow this simulator to overwrite the live history or v2 inventory.
    from z0.network.availability import DEFAULT_PATH as LIVE_PATH
    from z0.network.tracked_inventory import DEFAULT_PATH as INVENTORY_PATH

    if path.resolve() in {LIVE_PATH.resolve(), INVENTORY_PATH.resolve()}:
        raise ValueError("Simulation path must not be a production inventory file")

    hosts, events = load_simulation(path)
    ip = targets[0]
    record = hosts.get(ip, HostAvailability(address=ip))
    new_events: list[TransitionEvent] = []
    for symbol in sequence:
        stamp = datetime.now(UTC).isoformat()
        updated = transition(
            record, symbol == "S", timestamp=stamp,
            failure_threshold=failure_threshold,
            recovery_threshold=recovery_threshold,
        )
        if updated.state != record.state:
            event = TransitionEvent(
                address=ip, timestamp=stamp, old_state=record.state,
                new_state=updated.state,
                result="SUCCESS" if symbol == "S" else "FAILURE",
            )
            new_events.append(event)
        record = updated
    hosts[ip] = record
    events.extend(new_events)
    save_simulation(hosts, events, path)
    return record, new_events
