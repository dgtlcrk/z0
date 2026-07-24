"""Built-in infrastructure health plugin."""

from __future__ import annotations

from typing import Any

from z0.botops.config import load_config
from z0.botops.health import collect_health
from z0.plugins.base import Plugin, PluginMetadata


class HealthPlugin(Plugin):
    metadata = PluginMetadata(
        name="health",
        version="1.0.0",
        description="Check configured infrastructure targets",
    )

    def execute(self, action: str, **kwargs: Any) -> dict[str, Any]:
        if action != "check":
            raise ValueError(f"Unsupported health action: {action}")

        statuses = collect_health(load_config())

        return {
            "checks": [status.to_dict() for status in statuses],
        }


PLUGIN_CLASS = HealthPlugin
