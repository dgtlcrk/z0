"""Adapter registration and discovery."""

from __future__ import annotations

import os
from collections.abc import Iterable

from z0.adapters.base import Adapter, AdapterStatus
from z0.adapters.discord import DiscordAdapter
from z0.adapters.irc import IRCAdapter
from z0.botops.config import BotOpsConfig, load_config


class AdapterRegistry:
    """Store and manage available adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, Adapter] = {}

    def register(self, adapter: Adapter) -> None:
        name = adapter.name.lower()

        if name in self._adapters:
            raise ValueError(f"Adapter already registered: {name}")

        self._adapters[name] = adapter

    def get(self, name: str) -> Adapter:
        try:
            return self._adapters[name.lower()]
        except KeyError as error:
            raise KeyError(f"Unknown adapter: {name}") from error

    def names(self) -> list[str]:
        return sorted(self._adapters)

    def adapters(self) -> Iterable[Adapter]:
        for name in self.names():
            yield self._adapters[name]

    def statuses(self) -> list[AdapterStatus]:
        return [adapter.status() for adapter in self.adapters()]


def build_adapter_registry(
    config: BotOpsConfig | None = None,
) -> AdapterRegistry:
    config = config or load_config()

    registry = AdapterRegistry()

    registry.register(
        IRCAdapter(
            config.irc_host,
            config.irc_port,
            enabled=bool(config.irc_host),
            timeout=config.health_timeout,
        )
    )

    registry.register(
        DiscordAdapter(
            token=os.getenv("Z0_DISCORD_TOKEN", ""),
            enabled=config.discord_enabled,
        )
    )

    return registry
