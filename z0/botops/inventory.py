"""Hardware and network inventory collectors."""

from __future__ import annotations

import shutil
import socket
import subprocess
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InventoryInfo:
    ip_address: str
    mac_address: str
    serial_number: str
    docker_installed: str
    docker_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _ip_address() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)

    try:
        sock.connect(("1.1.1.1", 80))
        return str(sock.getsockname()[0])
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "N/A"
    finally:
        sock.close()


def _mac_address() -> str:
    value = uuid.getnode()
    return ":".join(f"{(value >> shift) & 0xff:02x}" for shift in range(40, -1, -8))


def _serial_number() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("serial"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass

    product_serial = Path("/sys/devices/virtual/dmi/id/product_serial")

    try:
        value = product_serial.read_text().strip()
        return value or "N/A"
    except OSError:
        return "N/A"


def _docker_info() -> tuple[str, str]:
    docker = shutil.which("docker")

    if not docker:
        return "NO", "N/A"

    try:
        result = subprocess.run(
            [docker, "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        )
        version = result.stdout.strip().replace("Docker version ", "")
        return "YES", version
    except (
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return "YES", "UNKNOWN"


def collect_inventory() -> InventoryInfo:
    docker_installed, docker_version = _docker_info()

    return InventoryInfo(
        ip_address=_ip_address(),
        mac_address=_mac_address(),
        serial_number=_serial_number(),
        docker_installed=docker_installed,
        docker_version=docker_version,
    )
