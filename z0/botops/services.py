"""Local and integration service-status collectors."""

from __future__ import annotations

import shutil
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from typing import Any

from z0.botops.config import BotOpsConfig


@dataclass(frozen=True)
class ServiceStatus:
    name: str
    status: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _systemd_active(*service_names: str) -> ServiceStatus:
    if not shutil.which("systemctl"):
        return ServiceStatus(service_names[0], "UNKNOWN", "systemctl unavailable")

    for name in service_names:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", name],
                capture_output=True,
                text=True,
                timeout=2,
            )

            if result.stdout.strip() == "active":
                return ServiceStatus(service_names[0], "RUNNING", name)
        except (OSError, subprocess.TimeoutExpired):
            break

    return ServiceStatus(service_names[0], "STOPPED")


def _docker_status() -> ServiceStatus:
    if not shutil.which("docker"):
        return ServiceStatus("Docker", "UNAVAILABLE")

    status = _systemd_active("docker")

    if status.status == "RUNNING":
        return ServiceStatus("Docker", "RUNNING")

    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        return ServiceStatus(
            "Docker",
            "RUNNING" if result.returncode == 0 else "STOPPED",
        )
    except (OSError, subprocess.TimeoutExpired):
        return ServiceStatus("Docker", "UNKNOWN")


def _tcp_service(name: str, host: str, port: int, timeout: float) -> ServiceStatus:
    if not host:
        return ServiceStatus(name, "UNCONFIGURED")

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return ServiceStatus(name, "REACHABLE", f"{host}:{port}")
    except OSError:
        return ServiceStatus(name, "OFFLINE", f"{host}:{port}")


def collect_services(config: BotOpsConfig) -> list[ServiceStatus]:
    with ThreadPoolExecutor(max_workers=3) as executor:
        ssh_future = executor.submit(_systemd_active, "ssh", "sshd")
        docker_future = executor.submit(_docker_status)
        irc_future = executor.submit(
            _tcp_service,
            "IRC",
            config.irc_host,
            config.irc_port,
            config.health_timeout,
        )

        statuses = [
            ServiceStatus("BotOps", "RUNNING"),
            ssh_future.result(),
            docker_future.result(),
            irc_future.result(),
            ServiceStatus(
                "Discord",
                "CONFIGURED" if config.discord_enabled else "UNCONFIGURED",
            ),
        ]

    normalized: list[ServiceStatus] = []

    for service in statuses:
        display_name = "SSH" if service.name in {"ssh", "sshd"} else service.name
        normalized.append(ServiceStatus(display_name, service.status, service.detail))

    return normalized
