"""System-information collectors used by BotOps."""

from __future__ import annotations

import platform
import shutil
import socket
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SystemInfo:
    hostname: str
    operating_system: str
    architecture: str
    python_version: str
    uptime: str
    cpu_temperature: str
    memory_usage: str
    disk_usage: str


def _uptime() -> str:
    try:
        seconds = int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return "N/A"

    days, remainder = divmod(seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes = remainder // 60

    if days:
        return f"{days}d {hours}h {minutes}m"

    return f"{hours}h {minutes}m"


def _memory_usage() -> str:
    try:
        values: dict[str, int] = {}

        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0])

        total = values["MemTotal"]
        available = values["MemAvailable"]

        if total <= 0:
            return "N/A"

        percentage = ((total - available) / total) * 100
        return f"{percentage:.0f}%"
    except (OSError, KeyError, ValueError):
        return "N/A"


def _disk_usage() -> str:
    try:
        usage = shutil.disk_usage("/")
        percentage = (usage.used / usage.total) * 100
        return f"{percentage:.0f}%"
    except (OSError, ZeroDivisionError):
        return "N/A"


def _cpu_temperature() -> str:
    paths = (
        Path("/sys/class/thermal/thermal_zone0/temp"),
        Path("/sys/devices/virtual/thermal/thermal_zone0/temp"),
    )

    for path in paths:
        try:
            value = float(path.read_text().strip())
            temperature = value / 1000 if value > 1000 else value
            return f"{temperature:.1f}°C"
        except (OSError, ValueError):
            continue

    return "N/A"


def collect_system_info() -> SystemInfo:
    return SystemInfo(
        hostname=socket.gethostname(),
        operating_system=f"{platform.system()} {platform.release()}",
        architecture=platform.machine(),
        python_version=platform.python_version(),
        uptime=_uptime(),
        cpu_temperature=_cpu_temperature(),
        memory_usage=_memory_usage(),
        disk_usage=_disk_usage(),
    )
