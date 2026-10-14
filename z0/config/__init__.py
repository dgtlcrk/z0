"""Shared configuration interface for the z0 platform."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

from .loader import config as platform_defaults

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Combined legacy IRC and platform configuration."""

    bot_name: str
    server: str
    port: int
    nickname: str
    channel: str
    use_tls: bool
    platform: Mapping[str, Any]

    @classmethod
    def from_env(
        cls,
        platform: Mapping[str, Any] | None = None,
    ) -> "Config":
        bot_name = os.getenv("BOT_NAME", "z0")

        return cls(
            bot_name=bot_name,
            server=os.getenv(
                "IRC_SERVER",
                "irc.prison.net",
            ),
            port=int(
                os.getenv(
                    "IRC_PORT",
                    "6667",
                )
            ),
            nickname=os.getenv(
                "IRC_NICK",
                bot_name,
            ),
            channel=os.getenv(
                "IRC_CHANNEL",
                "#skipland",
            ),
            use_tls=os.getenv("IRC_TLS", "false").strip().lower() in {
                "1", "true", "yes", "on"
            },
            platform=(
                platform
                if platform is not None
                else platform_defaults
            ),
        )

    def __getitem__(self, key: str) -> Any:
        """Provide mapping access for platform settings."""

        return self.platform[key]

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Return a platform setting with an optional default."""

        return self.platform.get(key, default)


config = Config.from_env()

# Compatibility alias used by older command modules.
BOT_NAME = config.bot_name

__all__ = [
    "BOT_NAME",
    "Config",
    "config",
]
