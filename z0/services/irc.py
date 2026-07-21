from __future__ import annotations

import irc.bot

from z0.config import config


class Z0Bot(irc.bot.SingleServerIRCBot):
    def __init__(self):
        super().__init__(
            [(config.server, config.port)],
            config.nickname,
            "z0 automation platform",
        )

    def on_welcome(self, connection, event):
        print(f"Connected to {config.server}")
        connection.join(config.channel)

    def on_join(self, connection, event):
        if event.source.nick == connection.get_nickname():
            print(f"Joined {config.channel}")

    def on_pubmsg(self, connection, event):
        message = event.arguments[0]

        if message == "!ping":
            connection.privmsg(event.target, "PONG")


def run():
    bot = Z0Bot()
    bot.start()
