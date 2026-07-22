"""Detect the current z0_n3t node and its operational role."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NodeInfo:
    platform: str
    role: str
    status: str


def _read_file(path: str) -> str:
    try:
        return Path(path).read_text(errors="ignore").strip()
    except OSError:
        return ""


def detect_node() -> NodeInfo:
    system = platform.system()

    if system == "Darwin":
        return NodeInfo(
            platform="MacBook Air",
            role="Development Workstation",
            status="ONLINE",
        )

    model = _read_file("/proc/device-tree/model")

    if "raspberry pi" in model.lower():
        return NodeInfo(
            platform=model.rstrip("\x00") or "Raspberry Pi",
            role="Edge Automation",
            status="ONLINE",
        )

    vendor = _read_file("/sys/devices/virtual/dmi/id/sys_vendor")
    product = _read_file("/sys/devices/virtual/dmi/id/product_name")
    cloud_identity = f"{vendor} {product}".lower()

    if any(name in cloud_identity for name in ("amazon", "ec2", "xen")):
        return NodeInfo(
            platform="AWS EC2",
            role="Cloud Automation",
            status="ONLINE",
        )

    if system == "Linux":
        return NodeInfo(
            platform="Linux Node",
            role="Network Operations",
            status="ONLINE",
        )

    return NodeInfo(
        platform=system or "Unknown",
        role="Automation Node",
        status="ONLINE",
    )
