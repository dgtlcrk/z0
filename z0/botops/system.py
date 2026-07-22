"""System-information collectors used by BotOps."""

from __future__ import annotations

import os
import platform
import shutil
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SystemInfo:
    hostname: str
    operating_system: str
    architecture: str
    python_version: str
    cpu_count: str
    uptime: str
    cpu_temperature: str
    memory_usage: str
    memory_total: str
    disk_usage: str
    disk_total: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _human_bytes(value: int) -> str:
    size = float(value)

    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            if unit in {"GiB", "TiB"}:
                return f"{size:.1f} {unit}"
            return f"{size:.0f} {unit}"

        size /= 1024

    return f"{value} B"


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

    if hours:
        return f"{hours}h {minutes}m"

    return f"{minutes}m"


def _memory() -> tuple[str, str]:
    try:
        values: dict[str, int] = {}

        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0]) * 1024

        total = values["MemTotal"]
        available = values["MemAvailable"]

        if total <= 0:
            return "N/A", "N/A"

        used_percentage = ((total - available) / total) * 100
        return f"{used_percentage:.0f}%", _human_bytes(total)
    except (OSError, KeyError, ValueError):
        return "N/A", "N/A"


def _disk() -> tuple[str, str]:
    try:
        usage = shutil.disk_usage("/")
        percentage = (usage.used / usage.total) * 100
        return f"{percentage:.0f}%", _human_bytes(usage.total)
    except (OSError, ZeroDivisionError):
        return "N/A", "N/A"


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
    memory_usage, memory_total = _memory()
    disk_usage, disk_total = _disk()

    return SystemInfo(
        hostname=socket.gethostname(),
        operating_system=f"{platform.system()} {platform.release()}",
        architecture=platform.machine(),
        python_version=platform.python_version(),
        cpu_count=str(os.cpu_count() or "N/A"),
        uptime=_uptime(),
        cpu_temperature=_cpu_temperature(),
        memory_usage=memory_usage,
        memory_total=memory_total,
        disk_usage=disk_usage,
        disk_total=disk_total,
    )
