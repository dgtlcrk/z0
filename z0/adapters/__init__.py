"""Communication adapter framework for z0."""

from z0.adapters.base import Adapter, AdapterStatus
from z0.adapters.registry import AdapterRegistry, build_adapter_registry

__all__ = [
    "Adapter",
    "AdapterRegistry",
    "AdapterStatus",
    "build_adapter_registry",
]
