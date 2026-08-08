"""Linux neighbor discovery for z0_n3t."""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Neighbor:
    ip_address: str
    mac_address: str
    interface: str
    state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run_ip_neigh() -> str:
    result = subprocess.run(
        ["ip", "neigh", "show"],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.stdout.strip()


def _parse_neighbor(line: str) -> Neighbor | None:
    parts = line.split()

    if not parts:
        return None

    ip_address = parts[0]

    interface = ""
    mac_address = ""

    if "dev" in parts:
        index = parts.index("dev")
        if index + 1 < len(parts):
            interface = parts[index + 1]

    if "lladdr" in parts:
        index = parts.index("lladdr")
        if index + 1 < len(parts):
            mac_address = parts[index + 1]

    state = parts[-1].upper()

    return Neighbor(
        ip_address=ip_address,
        mac_address=mac_address,
        interface=interface,
        state=state,
    )


def collect_neighbors() -> list[Neighbor]:
    neighbors: list[Neighbor] = []

    for line in _run_ip_neigh().splitlines():
        neighbor = _parse_neighbor(line)

        if neighbor is not None:
            neighbors.append(neighbor)

    return sorted(
        neighbors,
        key=lambda item: item.ip_address,
    )
