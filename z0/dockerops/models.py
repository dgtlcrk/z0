"""Docker data models used by the z0 operations platform."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DockerAvailability:
    """Docker engine availability result."""

    available: bool
    version: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ContainerSummary:
    """Summary of a Docker container."""

    container_id: str
    name: str
    image: str
    state: str
    status: str
    health: str
    ports: str
    created_at: str
    labels: str = ""

    @property
    def running(self) -> bool:
        return self.state.lower() == "running"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["running"] = self.running
        return payload


@dataclass(frozen=True, slots=True)
class ContainerStats:
    """Point-in-time Docker container resource statistics."""

    container_id: str
    name: str
    cpu_percent: str
    memory_usage: str
    memory_percent: str
    network_io: str
    block_io: str
    pids: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DockerSummary:
    """Docker engine and container summary."""

    available: bool
    version: str
    detail: str
    total: int
    running: int
    stopped: int
    unhealthy: int
    containers: list[ContainerSummary] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "version": self.version,
            "detail": self.detail,
            "total": self.total,
            "running": self.running,
            "stopped": self.stopped,
            "unhealthy": self.unhealthy,
            "containers": [
                container.to_dict()
                for container in self.containers
            ],
        }
