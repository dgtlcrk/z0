"""Command-line interface for z0_n3t BotOps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from z0.botops.config import DEFAULT_CONFIG_PATH, load_config
from z0.botops.git import collect_git_info
from z0.botops.health import collect_health
from z0.botops.inventory import collect_inventory
from z0.botops.node import detect_node
from z0.botops.render import PROJECT_ROOT, render_banner
from z0.botops.services import collect_services
from z0.botops.system import collect_system_info


def _snapshot(include_health: bool) -> dict[str, Any]:
    config = load_config()

    data: dict[str, Any] = {
        "node": detect_node(config).to_dict(),
        "system": collect_system_info().to_dict(),
        "inventory": collect_inventory().to_dict(),
        "services": [service.to_dict() for service in collect_services(config)],
        "project": collect_git_info(PROJECT_ROOT).to_dict(),
    }

    if include_health:
        data["infrastructure"] = [
            status.to_dict() for status in collect_health(config)
        ]

    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="z0-botops",
        description="z0_n3t operational dashboard and diagnostics",
    )

    subparsers = parser.add_subparsers(dest="command")

    banner = subparsers.add_parser("banner", help="Render the terminal dashboard")
    banner.add_argument(
        "--no-health",
        action="store_true",
        help="Skip external infrastructure checks",
    )

    status = subparsers.add_parser("status", help="Display the status dashboard")
    status.add_argument("--no-health", action="store_true")

    json_parser = subparsers.add_parser(
        "json",
        help="Output a machine-readable BotOps snapshot",
    )
    json_parser.add_argument("--no-health", action="store_true")
    json_parser.add_argument("--pretty", action="store_true")

    subparsers.add_parser("config", help="Show the BotOps configuration path")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    command = args.command or "banner"

    if command in {"banner", "status"}:
        print(render_banner(include_health=not getattr(args, "no_health", False)))
        return

    if command == "json":
        indent = 2 if args.pretty else None
        print(
            json.dumps(
                _snapshot(include_health=not args.no_health),
                indent=indent,
                sort_keys=True,
            )
        )
        return

    if command == "config":
        config_path = Path(DEFAULT_CONFIG_PATH)
        print(config_path)
        print("exists:", config_path.exists())
        return

    parser.error(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
