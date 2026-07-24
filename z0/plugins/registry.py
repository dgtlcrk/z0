"""Plugin discovery and execution."""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from z0.plugins.base import Plugin, PluginMetadata
from z0.plugins import builtin


class PluginRegistry:
    """Discover and manage z0 plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        name = plugin.metadata.name.lower()

        if name in self._plugins:
            raise ValueError(f"Plugin already registered: {name}")

        self._plugins[name] = plugin

    def discover_builtin(self) -> None:
        prefix = f"{builtin.__name__}."

        for module_info in pkgutil.iter_modules(
            builtin.__path__,
            prefix,
        ):
            module = importlib.import_module(module_info.name)
            plugin_class = getattr(module, "PLUGIN_CLASS", None)

            if plugin_class is None:
                continue

            self.register(plugin_class())

    def names(self) -> list[str]:
        return sorted(self._plugins)

    def metadata(self) -> list[PluginMetadata]:
        return [
            self._plugins[name].metadata
            for name in self.names()
        ]

    def execute(
        self,
        name: str,
        action: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            plugin = self._plugins[name.lower()]
        except KeyError as error:
            raise KeyError(f"Unknown plugin: {name}") from error

        if not plugin.metadata.enabled:
            raise RuntimeError(f"Plugin is disabled: {name}")

        return plugin.execute(action, **kwargs)


def build_plugin_registry() -> PluginRegistry:
    registry = PluginRegistry()
    registry.discover_builtin()
    return registry
