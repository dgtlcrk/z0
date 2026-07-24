"""Built-in system information plugin."""

from __future__ import annotations

from typing import Any

from z0.botops.system import collect_system_info
from z0.plugins.base import Plugin, PluginMetadata


class SystemPlugin(Plugin):
    metadata = PluginMetadata(
        name="system",
        version="1.0.0",
        description="Collect local system information",
    )

    def execute(self, action: str, **kwargs: Any) -> dict[str, Any]:
        if action not in {"status", "inventory"}:
            raise ValueError(f"Unsupported system action: {action}")

        return collect_system_info().to_dict()


PLUGIN_CLASS = SystemPlugin
