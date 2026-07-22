"""Render the z0_n3t BotOps terminal dashboard."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from z0.botops.git import collect_git_info
from z0.botops.node import detect_node
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


def render_banner() -> str:
    system = collect_system_info()
    git = collect_git_info(PROJECT_ROOT)
    node = detect_node()

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
                ("Hostname", system.hostname),
                ("Platform", node.platform),
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
                ("Python", system.python_version),
                ("Uptime", system.uptime),
                ("CPU Temp", system.cpu_temperature),
                ("Memory", system.memory_usage),
                ("Disk", system.disk_usage),
            ],
        ),
        "",
        *_section(
            " PROJECT",
            [
                ("Repository", git.repository),
                ("Branch", git.branch),
                ("Commit", git.commit),
                ("Git Status", git.status),
                ("Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ],
        ),
        "═" * WIDTH,
        "",
        ">>> Welcome to z0_n3t",
    ]

    return "\n".join(lines)
