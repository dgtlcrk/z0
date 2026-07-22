"""Configuration loading for the z0_n3t BotOps subsystem."""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "z0" / "botops.env"


def _load_env_file(path: Path) -> None:
    """Load simple KEY=value settings without overriding exported variables."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for raw_line in lines:
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")

        if key:
            os.environ.setdefault(key, value)


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class BotOpsConfig:
    node_name: str
    node_role: str
    irc_host: str
    irc_port: int
    discord_enabled: bool
    aws_host: str
    domain: str
    health_timeout: float
    github_host: str
    show_health_on_login: bool


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> BotOpsConfig:
    _load_env_file(path)

    return BotOpsConfig(
        node_name=os.getenv("Z0_NODE_NAME", socket.gethostname()),
        node_role=os.getenv("Z0_NODE_ROLE", ""),
        irc_host=os.getenv("Z0_IRC_HOST", ""),
        irc_port=_get_int("Z0_IRC_PORT", 6697),
        discord_enabled=_get_bool("Z0_DISCORD_ENABLED"),
        aws_host=os.getenv("Z0_AWS_HOST", ""),
        domain=os.getenv("Z0_DOMAIN", ""),
        health_timeout=max(_get_float("Z0_HEALTH_TIMEOUT", 1.5), 0.25),
        github_host=os.getenv("Z0_GITHUB_HOST", "github.com"),
        show_health_on_login=_get_bool("Z0_SHOW_HEALTH_ON_LOGIN", True),
    )
