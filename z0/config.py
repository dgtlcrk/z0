from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Runtime configuration loaded from environment variables."""

    bot_name: str
    server: str
    port: int
    nickname: str
    channel: str

    @classmethod
    def from_env(cls) -> "Config":
        bot_name = os.getenv("BOT_NAME", "z0")

        return cls(
            bot_name=bot_name,
            server=os.getenv("IRC_SERVER", "irc.prison.net"),
            port=int(os.getenv("IRC_PORT", "6667")),
            nickname=os.getenv("IRC_NICK", bot_name),
            channel=os.getenv("IRC_CHANNEL", "#skipland"),
        )


config = Config.from_env()

# Compatibility alias for existing imports.
BOT_NAME = config.bot_name
