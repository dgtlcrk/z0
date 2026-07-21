from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Config:
    server: str
    port: int
    nickname: str
    channel: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            server=os.getenv("IRC_SERVER", "irc.prison.net"),
            port=int(os.getenv("IRC_PORT", "6667")),
            nickname=os.getenv("IRC_NICK", "z0"),
            channel=os.getenv("IRC_CHANNEL", "#skipland"),
        )


config = Config.from_env()
