from __future__ import annotations

from collections.abc import Callable

import irc.bot

from z0.commands import core
from z0.commands import network as network_commands
from z0.commands import system as system_commands
from z0.config import config

MAX_IRC_MESSAGE_LENGTH = 350


class Z0Bot(irc.bot.SingleServerIRCBot):
    def __init__(self) -> None:
        super().__init__(
            [(config.server, config.port)],
            config.nickname,
            "z0 automation platform",
        )

    def on_welcome(self, connection, event) -> None:
        print(f"Connected to {config.server}", flush=True)
        connection.join(config.channel)

    def on_join(self, connection, event) -> None:
        if event.source.nick == connection.get_nickname():
            print(f"Joined {config.channel}", flush=True)

    def on_disconnect(self, connection, event) -> None:
        print("Disconnected from IRC; reconnecting automatically", flush=True)

    def send_response(self, connection, target: str, response: str) -> None:
        """Send responses safely within practical IRC message limits."""
        for original_line in response.splitlines() or [""]:
            line = original_line.strip()

            if not line:
                continue

            while len(line) > MAX_IRC_MESSAGE_LENGTH:
                split_at = line.rfind(" ", 0, MAX_IRC_MESSAGE_LENGTH)

                if split_at <= 0:
                    split_at = MAX_IRC_MESSAGE_LENGTH

                connection.privmsg(target, line[:split_at])
                line = line[split_at:].lstrip()

            if line:
                connection.privmsg(target, line)

    def on_pubmsg(self, connection, event) -> None:
        raw_message = event.arguments[0].strip()

        if not raw_message.startswith("!"):
            return

        parts = raw_message.split(maxsplit=1)
        command = parts[0].lower()
        argument = parts[1].strip() if len(parts) == 2 else ""

        print(
            f"Command from {event.source.nick} "
            f"in {event.target}: {raw_message}",
            flush=True,
        )

        no_argument_commands: dict[str, Callable[[], str]] = {
            "!help": core.help_text,
            "!uptime": core.uptime,
            "!about": core.about,
            "!hostname": system_commands.hostname,
            "!time": system_commands.current_time,
            "!version": system_commands.version,
            "!memory": system_commands.memory,
            "!disk": system_commands.disk,
        }

        handler = no_argument_commands.get(command)

        if handler is not None:
            response = handler()
        elif command == "!ping":
            response = (
                network_commands.ping(argument)
                if argument
                else core.ping()
            )
        elif command == "!dns":
            response = network_commands.dns(argument)
        elif command == "!whois":
            response = network_commands.whois(argument)
        elif command == "!trace":
            response = network_commands.trace(argument)
        else:
            response = "Unknown command. Use !help"

        self.send_response(connection, event.target, response)


def run() -> None:
    print(
        f"Starting z0: server={config.server}:{config.port} "
        f"nick={config.nickname} channel={config.channel}",
        flush=True,
    )

    bot = Z0Bot()

    print("IRC client initialized; connecting...", flush=True)
    bot.start()
