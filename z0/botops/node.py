"""Detect the current z0_n3t node and operational role."""

from __future__ import annotations

import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from z0.botops.config import BotOpsConfig


@dataclass(frozen=True)
class NodeInfo:
    name: str
    platform: str
    node_type: str
    role: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_file(path: str) -> str:
    try:
        return Path(path).read_text(errors="ignore").strip().rstrip("\x00")
    except OSError:
        return ""


def detect_node(config: BotOpsConfig) -> NodeInfo:
    system = platform.system()
    configured_role = config.node_role.strip()

    if system == "Darwin":
        return NodeInfo(
            name=config.node_name,
            platform="MacBook Air",
            node_type="workstation",
            role=configured_role or "Development Workstation",
            status="ONLINE",
        )

    model = _read_file("/proc/device-tree/model")

    if "raspberry pi" in model.lower():
        return NodeInfo(
            name=config.node_name,
            platform=model or "Raspberry Pi",
            node_type="edge",
            role=configured_role or "Edge Automation",
            status="ONLINE",
        )

    vendor = _read_file("/sys/devices/virtual/dmi/id/sys_vendor")
    product = _read_file("/sys/devices/virtual/dmi/id/product_name")
    cloud_identity = f"{vendor} {product}".lower()

    if any(name in cloud_identity for name in ("amazon", "ec2", "xen")):
        return NodeInfo(
            name=config.node_name,
            platform="AWS EC2",
            node_type="cloud",
            role=configured_role or "Cloud Automation",
            status="ONLINE",
        )

    if system == "Linux":
        return NodeInfo(
            name=config.node_name,
            platform=product or "Linux Node",
            node_type="linux",
            role=configured_role or "Network Operations",
            status="ONLINE",
        )

    return NodeInfo(
        name=config.node_name,
        platform=system or "Unknown",
        node_type="unknown",
        role=configured_role or "Automation Node",
        status="ONLINE",
    )
