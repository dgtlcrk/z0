from __future__ import annotations

import platform
import shutil
import socket
from datetime import datetime


def hostname() -> str:
    """Return the container hostname."""
    return f"Hostname: {socket.gethostname()}"


def current_time() -> str:
    """Return the container's current local time."""
    now = datetime.now().astimezone()
    return f"Time: {now.strftime('%Y-%m-%d %I:%M:%S %p %Z')}"


def version() -> str:
    """Return Python and operating-system versions."""
    return (
        f"Python {platform.python_version()} | "
        f"{platform.system()} {platform.release()} | "
        f"{platform.machine()}"
    )


def memory() -> str:
    """Return Linux memory utilization."""
    try:
        values: dict[str, int] = {}

        with open("/proc/meminfo", encoding="utf-8") as file:
            for line in file:
                key, value = line.split(":", 1)
                values[key] = int(value.strip().split()[0])

        total_kib = values["MemTotal"]
        available_kib = values["MemAvailable"]
        used_kib = total_kib - available_kib

        total_mib = total_kib / 1024
        used_mib = used_kib / 1024
        percent = used_kib / total_kib * 100

        return (
            f"Memory: {used_mib:.0f} MiB used / "
            f"{total_mib:.0f} MiB total ({percent:.1f}%)"
        )
    except (OSError, KeyError, ValueError) as error:
        return f"Memory lookup failed: {error}"


def disk() -> str:
    """Return root filesystem utilization."""
    try:
        usage = shutil.disk_usage("/")

        gib = 1024**3
        total = usage.total / gib
        used = usage.used / gib
        free = usage.free / gib
        percent = usage.used / usage.total * 100

        return (
            f"Disk: {used:.1f} GiB used / {total:.1f} GiB total "
            f"({free:.1f} GiB free, {percent:.1f}%)"
        )
    except OSError as error:
        return f"Disk lookup failed: {error}"
