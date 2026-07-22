"""Infrastructure reachability and health checks."""

from __future__ import annotations

import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from typing import Any

from z0.botops.config import BotOpsConfig


@dataclass(frozen=True)
class HealthStatus:
    name: str
    status: str
    target: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _dns_check(name: str, host: str) -> HealthStatus:
    if not host:
        return HealthStatus(name, "UNCONFIGURED", "")

    try:
        socket.getaddrinfo(host, None)
        return HealthStatus(name, "ONLINE", host)
    except socket.gaierror:
        return HealthStatus(name, "OFFLINE", host)


def _tcp_check(name: str, host: str, port: int, timeout: float) -> HealthStatus:
    if not host:
        return HealthStatus(name, "UNCONFIGURED", "")

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return HealthStatus(name, "ONLINE", f"{host}:{port}")
    except OSError:
        return HealthStatus(name, "OFFLINE", f"{host}:{port}")


def collect_health(config: BotOpsConfig) -> list[HealthStatus]:
    checks = {
        "GitHub": lambda: _tcp_check(
            "GitHub",
            config.github_host,
            443,
            config.health_timeout,
        ),
        "AWS": lambda: _tcp_check(
            "AWS",
            config.aws_host,
            443,
            config.health_timeout,
        ),
        "Domain": lambda: _dns_check("Domain", config.domain),
    }

    with ThreadPoolExecutor(max_workers=len(checks)) as executor:
        futures = {
            name: executor.submit(check)
            for name, check in checks.items()
        }

        return [futures[name].result() for name in checks]
