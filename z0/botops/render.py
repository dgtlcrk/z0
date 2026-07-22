"""Render the z0_n3t BotOps terminal dashboard."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from z0.botops.config import BotOpsConfig, load_config
from z0.botops.git import collect_git_info
from z0.botops.health import HealthStatus, collect_health
from z0.botops.inventory import collect_inventory
from z0.botops.node import detect_node
from z0.botops.services import ServiceStatus, collect_services
from z0.botops.system import collect_system_info


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WIDTH = 68

LOGO = r"""
███████╗ ██████╗        ███╗   ██╗██████╗ ███████╗████████╗
╚══███╔╝██╔═████╗       ████╗  ██║╚════██╗██╔════╝╚══██╔══╝
  ███╔╝ ██║██╔██║█████╗██╔██╗ ██║ █████╔╝█████╗     ██║
 ███╔╝  ████╔╝██║╚════╝██║╚██╗██║ ╚═══██╗██╔══╝     ██║
███████╗╚██████╔╝      ██║ ╚████║██████╔╝███████╗   ██║
╚══════╝ ╚═════╝       ╚═╝  ╚═══╝╚═════╝ ╚══════╝   ╚═╝
""".strip("\n")


def _section(title: str, rows: list[tuple[str, str]]) -> list[str]:
    lines = [title, "─" * WIDTH]

    for label, value in rows:
        lines.append(f" {label:<12} : {value}")

    return lines


def _service_marker(status: str) -> str:
    if status in {"RUNNING", "ONLINE", "REACHABLE", "CONFIGURED"}:
        return "●"

    if status in {"UNCONFIGURED", "UNAVAILABLE", "UNKNOWN"}:
        return "○"

    return "×"


def _service_rows(services: list[ServiceStatus]) -> list[tuple[str, str]]:
    return [
        (
            service.name,
            f"{_service_marker(service.status)} {service.status}"
            + (f" ({service.detail})" if service.detail else ""),
        )
        for service in services
    ]


def _health_rows(statuses: list[HealthStatus]) -> list[tuple[str, str]]:
    return [
        (
            status.name,
            f"{_service_marker(status.status)} {status.status}"
            + (f" ({status.target})" if status.target else ""),
        )
        for status in statuses
    ]


def render_banner(
    *,
    include_health: bool = True,
    config: BotOpsConfig | None = None,
) -> str:
    config = config or load_config()
    system = collect_system_info()
    git = collect_git_info(PROJECT_ROOT)
    node = detect_node(config)
    inventory = collect_inventory()
    services = collect_services(config)

    lines = [
        LOGO,
        "",
        "z0_n3t".center(WIDTH),
        "Network Automation Platform".center(WIDTH),
        "",
        "IRC • Discord • AWS • Linux • Python".center(WIDTH),
        "",
        "═" * WIDTH,
        *_section(
            " NODE",
            [
                ("Name", node.name),
                ("Hostname", system.hostname),
                ("Platform", node.platform),
                ("Type", node.node_type),
                ("Role", node.role),
                ("Status", node.status),
            ],
        ),
        "",
        *_section(
            " SYSTEM",
            [
                ("OS", system.operating_system),
                ("Architecture", system.architecture),
                ("CPU Cores", system.cpu_count),
                ("Python", system.python_version),
                ("Uptime", system.uptime),
                ("CPU Temp", system.cpu_temperature),
                ("Memory", f"{system.memory_usage} of {system.memory_total}"),
                ("Disk", f"{system.disk_usage} of {system.disk_total}"),
            ],
        ),
        "",
        *_section(
            " INVENTORY",
            [
                ("IP Address", inventory.ip_address),
                ("MAC Address", inventory.mac_address),
                ("Serial", inventory.serial_number),
                ("Docker", inventory.docker_installed),
                ("Docker Ver.", inventory.docker_version),
            ],
        ),
        "",
        *_section(" SERVICES", _service_rows(services)),
    ]

    if include_health:
        lines.extend(
            [
                "",
                *_section(" INFRASTRUCTURE", _health_rows(collect_health(config))),
            ]
        )

    lines.extend(
        [
            "",
            *_section(
                " PROJECT",
                [
                    ("Repository", git.repository),
                    ("Branch", git.branch),
                    ("Commit", git.commit),
                    ("Git Status", git.status),
                    ("Remote", git.remote),
                    ("Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                ],
            ),
            "═" * WIDTH,
            "",
            ">>> Welcome to z0_n3t",
        ]
    )

    return "\n".join(lines)
