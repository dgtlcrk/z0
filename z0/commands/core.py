from __future__ import annotations

import platform
import time

from z0.config import config

START_TIME = time.monotonic()


def ping() -> str:
    """Respond to !ping without a target."""
    return "PONG"


def help_text() -> str:
    """List available commands."""
    return (
        "Commands: !help !ping !uptime !about "
        "!hostname !time !version !memory !disk "
        "!dns <host> !whois <domain> !ping <host> !trace <host>"
    )


def uptime() -> str:
    """Return the bot process uptime."""
    elapsed = int(time.monotonic() - START_TIME)

    days, remainder = divmod(elapsed, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days:
        return f"Uptime: {days}d {hours}h {minutes}m {seconds}s"

    return f"Uptime: {hours}h {minutes}m {seconds}s"


def about() -> str:
    """Return information about the bot identity and Python runtime."""
    return (
        f"{config.bot_name} • Python {platform.python_version()} • "
        "Network Automation Platform"
    )
