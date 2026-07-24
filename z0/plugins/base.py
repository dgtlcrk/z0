"""Plugin interfaces for z0."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PluginMetadata:
    name: str
    version: str
    description: str
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Plugin(ABC):
    """Base class for dynamically discoverable z0 plugins."""

    metadata: PluginMetadata

    @abstractmethod
    def execute(self, action: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a plugin action."""
