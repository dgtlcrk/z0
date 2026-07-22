#!/usr/bin/env python3

from __future__ import annotations

import platform
import shutil
import socket
import subprocess
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_command(command: list[str]) -> str:
    try:
        return subprocess.check_output(
            command,
            cwd=PROJECT_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "N/A"


def git_branch() -> str:
    return run_command(["git", "branch", "--show-current"])


def git_commit() -> str:
    return run_command(["git", "rev-parse", "--short", "HEAD"])


def git_status() -> str:
    result = run_command(["git", "status", "--porcelain"])

    if result == "N/A":
        return "N/A"

    return "DIRTY" if result else "CLEAN"


def uptime() -> str:
    try:
        seconds = float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return "N/A"

    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60

    if days:
        return f"{days}d {hours}h {minutes}m"

    return f"{hours}h {minutes}m"


def memory_usage() -> str:
    try:
        lines = Path("/proc/meminfo").read_text().splitlines()
        values = {}

        for line in lines:
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0])

        total = values["MemTotal"]
        available = values["MemAvailable"]
        used_percent = ((total - available) / total) * 100
        return f"{used_percent:.0f}%"
    except (OSError, KeyError, ValueError):
        return "N/A"


def disk_usage() -> str:
    usage = shutil.disk_usage("/")
    used_percent = (usage.used / usage.total) * 100
    return f"{used_percent:.0f}%"


def cpu_temperature() -> str:
    thermal_file = Path("/sys/class/thermal/thermal_zone0/temp")

    try:
        temperature = int(thermal_file.read_text().strip()) / 1000
        return f"{temperature:.1f}°C"
    except (OSError, ValueError):
        return "N/A"


def print_banner() -> None:
    print(
        r"""
███████╗ ██████╗        ███╗   ██╗██████╗ ███████╗████████╗
╚══███╔╝██╔═████╗       ████╗  ██║╚════██╗██╔════╝╚══██╔══╝
  ███╔╝ ██║██╔██║█████╗██╔██╗ ██║ █████╔╝█████╗     ██║
 ███╔╝  ████╔╝██║╚════╝██║╚██╗██║ ╚═══██╗██╔══╝     ██║
███████╗╚██████╔╝      ██║ ╚████║██████╔╝███████╗   ██║
╚══════╝ ╚═════╝       ╚═╝  ╚═══╝╚═════╝ ╚══════╝   ╚═╝

                     z0_n3t

             Network Automation Platform

          IRC • Discord • AWS • Linux • Python
"""
    )

    print("─" * 68)
    print(" NODE")
    print("─" * 68)
    print(f" Hostname     : {socket.gethostname()}")
    print(f" Operating OS : {platform.system()} {platform.release()}")
    print(f" Architecture : {platform.machine()}")
    print(f" Python       : {platform.python_version()}")
    print(f" Uptime       : {uptime()}")
    print()

    print(" SYSTEM")
    print("─" * 68)
    print(f" CPU Temp     : {cpu_temperature()}")
    print(f" Memory       : {memory_usage()}")
    print(f" Disk         : {disk_usage()}")
    print()

    print(" PROJECT")
    print("─" * 68)
    print(f" Repository   : {PROJECT_ROOT.name}")
    print(f" Branch       : {git_branch()}")
    print(f" Commit       : {git_commit()}")
    print(f" Git Status   : {git_status()}")
    print(f" Time         : {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("─" * 68)
    print()
    print(">>> Welcome to z0_n3t")


def main() -> None:
    print_banner()


if __name__ == "__main__":
    main()
