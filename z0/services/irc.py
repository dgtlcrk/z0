from __future__ import annotations

import json
import os
import secrets
import ssl
import time
from collections.abc import Callable
from functools import partial
from pathlib import Path

import irc.bot
import irc.connection

from z0.commands import core
from z0.commands import network as network_commands
from z0.commands import system as system_commands
from z0.config import config
from z0.services.op_auth import OpAuthenticator

MAX_IRC_MESSAGE_LENGTH = 350
IRC_HEARTBEAT_INTERVAL_SECONDS = 60
IRC_HEARTBEAT_TIMEOUT_SECONDS = 30
IRC_HEARTBEAT_CHECK_SECONDS = 5


def create_irc_ssl_context() -> ssl.SSLContext:
    """Load system trust plus an independently verified IRC server PEM."""
    context = ssl.create_default_context()
    custom_ca = os.getenv("IRC_TLS_CA_PEM", "").strip()
    if custom_ca:
        context.load_verify_locations(cadata=custom_ca)
    return context



def valid_irc_alert_message(message: object) -> bool:
    """Permit one safe IRC line from the local spool."""
    return (
        isinstance(message, str)
        and message.startswith("z0_n3t ")
        and len(message) <= MAX_IRC_MESSAGE_LENGTH
        and not any(char in message for char in "\r\n\x00")
    )


class Z0Bot(irc.bot.SingleServerIRCBot):
    def __init__(self) -> None:
        secret = os.getenv("IRC_OP_SECRET", "")
        self.op_auth = OpAuthenticator(secret, config.channel) if secret else None
        self._alert_poll_scheduled = False
        self._heartbeat_poll_scheduled = False
        self._heartbeat_pending: str | None = None
        self._heartbeat_deadline = 0.0
        self._heartbeat_next_due = 0.0
        self.autoop_hostmask = os.getenv("IRC_AUTOOP_HOSTMASK", "").strip().lower()
        connect_factory = (
            irc.connection.Factory(
                wrapper=partial(
                    create_irc_ssl_context().wrap_socket,
                    server_hostname=config.server,
                )
            )
            if config.use_tls
            else irc.connection.Factory()
        )
        super().__init__(
            [(config.server, config.port)],
            config.nickname,
            f"{config.bot_name} automation platform",
            connect_factory=connect_factory,
        )

    def _drain_alert_spool(self) -> None:
        """Drain host-queued alerts over this bot's existing IRC connection."""
        directory = os.environ.get("Z0_IRC_ALERT_SPOOL", "")
        if not directory:
            return
        spool = Path(directory)
        if not (spool / "acks").is_dir():
            return
        connection = self.connection
        if not connection.is_connected():
            return
        for path in sorted((spool / "pending").glob("*.json"))[:16]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                message = payload["message"]
                if not valid_irc_alert_message(message):
                    raise ValueError("Invalid IRC alert payload")
                # Send only to the channel already configured for this bot.
                self.send_response(connection, config.channel, message)
                receipt = spool / "acks" / (path.stem + ".ack")
                receipt.touch(exist_ok=True)
                path.unlink()
            except (OSError, ValueError, KeyError, TypeError) as exc:
                print(f"IRC alert queue item skipped: {type(exc).__name__}",
                      flush=True)

    def _check_irc_heartbeat(self) -> None:
        """Detect stale IRC sessions even when TCP still appears connected."""
        connection = self.connection
        if not connection.is_connected():
            return
        now = time.monotonic()
        if self._heartbeat_pending is not None:
            if now >= self._heartbeat_deadline:
                print("IRC heartbeat timed out; forcing reconnect", flush=True)
                self._heartbeat_pending = None
                connection.disconnect("IRC heartbeat timeout")
            return
        if now < self._heartbeat_next_due:
            return
        token = "z0-" + secrets.token_hex(8)
        self._heartbeat_pending = token
        self._heartbeat_deadline = now + IRC_HEARTBEAT_TIMEOUT_SECONDS
        try:
            connection.ping(token)
        except (OSError, RuntimeError) as exc:
            print(f"IRC heartbeat send failed: {type(exc).__name__}", flush=True)
            self._heartbeat_pending = None
            connection.disconnect("IRC heartbeat send failed")

    def on_pong(self, connection, event) -> None:
        """Accept only the matching response for the current heartbeat."""
        if (
            connection is self.connection
            and self._heartbeat_pending is not None
            and event.arguments
            and event.arguments[-1].lstrip(":") == self._heartbeat_pending
        ):
            self._heartbeat_pending = None
            self._heartbeat_deadline = 0.0
            self._heartbeat_next_due = (
                time.monotonic() + IRC_HEARTBEAT_INTERVAL_SECONDS
            )

    def on_welcome(self, connection, event) -> None:
        print(f"Connected to {config.server}", flush=True)
        self._heartbeat_pending = None
        self._heartbeat_deadline = 0.0
        self._heartbeat_next_due = time.monotonic() + IRC_HEARTBEAT_INTERVAL_SECONDS
        if not self._heartbeat_poll_scheduled:
            self.reactor.scheduler.execute_every(
                IRC_HEARTBEAT_CHECK_SECONDS, self._check_irc_heartbeat
            )
            self._heartbeat_poll_scheduled = True
        connection.join(config.channel)
        if (os.environ.get('Z0_IRC_ALERT_SPOOL')
                and not self._alert_poll_scheduled):
            self.reactor.scheduler.execute_every(5, self._drain_alert_spool)
            self._alert_poll_scheduled = True

    def on_join(self, connection, event) -> None:
        if event.source.nick == connection.get_nickname():
            print(f"Joined {config.channel}", flush=True)
            return

        # Require exact nick!user@host; a nickname alone is not trustworthy.
        # This allowlist is a convenience, not cryptographic authentication.
        if (
            self.autoop_hostmask
            and event.target.lower() == config.channel.lower()
            and str(event.source).lower() == self.autoop_hostmask
        ):
            connection.mode(config.channel, f"+o {event.source.nick}")
            print("Auto-OP requested for configured IRC identity", flush=True)

    def on_disconnect(self, connection, event) -> None:
        self._heartbeat_pending = None
        self._heartbeat_deadline = 0.0
        self._heartbeat_next_due = 0.0
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

    def on_privmsg(self, connection, event) -> None:
        """Handle OP requests only in private messages."""
        parts = event.arguments[0].strip().split()
        nick = event.source.nick
        if not parts or parts[0].lower() != "op":
            self.send_response(
                connection, nick, "Usage: op #channel | op #channel <hmac>"
            )
            return
        if self.op_auth is None:
            self.send_response(connection, nick, "OP authentication is disabled")
            return
        if len(parts) == 2:
            _, response = self.op_auth.challenge(str(event.source), parts[1])
            self.send_response(connection, nick, response)
            return
        if len(parts) == 3:
            channel, digest = parts[1:]
            if not self.op_auth.verify(str(event.source), channel, digest):
                self.send_response(connection, nick, "Authentication failed or expired")
                return
            connection.mode(self.op_auth.channel, f"+o {nick}")
            self.send_response(connection, nick, "Operator mode requested")
            return
        self.send_response(connection, nick, "Usage: op #channel | op #channel <hmac>")

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
        f"Starting {config.bot_name}: server={config.server}:{config.port} "
        f"nick={config.nickname} channel={config.channel} "
        f"tls={config.use_tls}",
        flush=True,
    )

    bot = Z0Bot()

    print("IRC client initialized; connecting...", flush=True)
    bot.start()
