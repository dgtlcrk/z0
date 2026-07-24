"""Plugin framework for z0."""

from z0.plugins.base import Plugin, PluginMetadata
from z0.plugins.registry import PluginRegistry, build_plugin_registry

__all__ = [
    "Plugin",
    "PluginMetadata",
    "PluginRegistry",
    "build_plugin_registry",
]
