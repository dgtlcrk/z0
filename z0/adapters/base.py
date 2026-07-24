"""Base interfaces for z0 communication adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AdapterStatus:
    """Runtime status returned by an adapter."""

    name: str
    enabled: bool
    connected: bool
    state: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Adapter(ABC):
    """Common interface implemented by all communication adapters."""

    name = "adapter"

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    @abstractmethod
    def connect(self) -> None:
        """Connect the adapter."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect the adapter."""

    @abstractmethod
    def send(self, destination: str, message: str) -> None:
        """Send a message through the adapter."""

    @abstractmethod
    def status(self) -> AdapterStatus:
        """Return the current adapter status."""
