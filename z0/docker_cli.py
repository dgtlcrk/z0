"""Command-line interface for z0 Docker operations."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from z0.core import (
    CommandExecutionError,
    ValidationError,
    dumps,
)
from z0.dockerops import DockerClient


def _print_json(
    value: Any,
    *,
    pretty: bool,
) -> None:
    print(
        dumps(
            value,
            pretty=pretty,
        )
    )


def _truncate(
    value: str,
    width: int,
) -> str:
    if len(value) <= width:
        return value

    return value[: max(0, width - 3)] + "..."


def _print_container_table(
    containers: list[dict[str, Any]],
) -> None:
    if not containers:
        print("No Docker containers found.")
        return

    header = (
        f"{'NAME':<20} "
        f"{'STATE':<10} "
        f"{'HEALTH':<10} "
        f"{'IMAGE':<32} "
        f"{'PORTS'}"
    )

    print(header)
    print("-" * min(len(header), 110))

    for container in containers:
        print(
            f"{_truncate(str(container['name']), 20):<20} "
            f"{_truncate(str(container['state']), 10):<10} "
            f"{_truncate(str(container['health']), 10):<10} "
            f"{_truncate(str(container['image']), 32):<32} "
            f"{container['ports']}"
        )


def _print_stats_table(
    records: list[dict[str, Any]],
) -> None:
    if not records:
        print("No Docker statistics returned.")
        return

    header = (
        f"{'NAME':<20} "
        f"{'CPU':>9} "
        f"{'MEMORY':<28} "
        f"{'MEM %':>9} "
        f"{'PIDS':>6}"
    )

    print(header)
    print("-" * len(header))

    for record in records:
        print(
            f"{_truncate(str(record['name']), 20):<20} "
            f"{str(record['cpu_percent']):>9} "
            f"{_truncate(str(record['memory_usage']), 28):<28} "
            f"{str(record['memory_percent']):>9} "
            f"{str(record['pids']):>6}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="z0 docker",
        description="Docker operations for the z0 platform",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output compact JSON",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Output formatted JSON",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "status",
        help="Show Docker engine and container status",
    )

    ps_parser = subparsers.add_parser(
        "ps",
        help="List Docker containers",
    )
    ps_parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Include stopped containers",
    )

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect a Docker container",
    )
    inspect_parser.add_argument(
        "container",
        help="Container name or ID",
    )

    stats_parser = subparsers.add_parser(
        "stats",
        help="Show point-in-time container statistics",
    )
    stats_parser.add_argument(
        "containers",
        nargs="*",
        help="Optional container names or IDs",
    )

    logs_parser = subparsers.add_parser(
        "logs",
        help="Show recent container logs",
    )
    logs_parser.add_argument(
        "container",
        help="Container name or ID",
    )
    logs_parser.add_argument(
        "--tail",
        type=int,
        default=100,
        help="Number of log lines to return",
    )
    logs_parser.add_argument(
        "--timestamps",
        action="store_true",
        help="Include Docker log timestamps",
    )

    restart_parser = subparsers.add_parser(
        "restart",
        help="Restart a Docker container",
    )
    restart_parser.add_argument(
        "container",
        help="Container name or ID",
    )
    restart_parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Seconds to wait before forcefully stopping",
    )
    restart_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation",
    )

    subparsers.add_parser(
        "info",
        help="Show Docker engine information",
    )

    return parser


def _confirm_restart(
    container: str,
) -> bool:
    if not sys.stdin.isatty():
        print(
            "Restart refused: use --yes in "
            "non-interactive mode.",
            file=sys.stderr,
        )
        return False

    response = input(
        f"Restart Docker container {container!r}? [y/N] "
    )

    return response.strip().lower() in {
        "y",
        "yes",
    }


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    client = DockerClient()

    json_output = bool(
        args.json
        or args.pretty
    )

    try:
        if args.command == "status":
            result = client.summary().to_dict()

            if json_output:
                _print_json(
                    result,
                    pretty=args.pretty,
                )
            else:
                print("Docker")
                print(
                    f"  Status    : "
                    f"{'ONLINE' if result['available'] else 'OFFLINE'}"
                )
                print(
                    f"  Version   : "
                    f"{result['version'] or 'UNKNOWN'}"
                )
                print(
                    f"  Containers: {result['total']}"
                )
                print(
                    f"  Running   : {result['running']}"
                )
                print(
                    f"  Stopped   : {result['stopped']}"
                )
                print(
                    f"  Unhealthy : {result['unhealthy']}"
                )

                if result["detail"]:
                    print(
                        f"  Detail    : {result['detail']}"
                    )

            return (
                0
                if result["available"]
                else 1
            )

        if args.command == "ps":
            containers = [
                container.to_dict()
                for container in client.list_containers(
                    all_containers=args.all
                )
            ]

            if json_output:
                _print_json(
                    containers,
                    pretty=args.pretty,
                )
            else:
                _print_container_table(
                    containers
                )

            return 0

        if args.command == "inspect":
            result = client.inspect(
                args.container
            )

            _print_json(
                result,
                pretty=True,
            )

            return 0

        if args.command == "stats":
            statistics = [
                record.to_dict()
                for record in client.stats(
                    args.containers
                )
            ]

            if json_output:
                _print_json(
                    statistics,
                    pretty=args.pretty,
                )
            else:
                _print_stats_table(
                    statistics
                )

            return 0

        if args.command == "logs":
            logs = client.logs(
                args.container,
                tail=args.tail,
                timestamps=args.timestamps,
            )

            if json_output:
                _print_json(
                    {
                        "container": args.container,
                        "tail": args.tail,
                        "logs": logs,
                    },
                    pretty=args.pretty,
                )
            else:
                print(logs)

            return 0

        if args.command == "restart":
            if (
                not args.yes
                and not _confirm_restart(
                    args.container
                )
            ):
                print(
                    "Restart cancelled.",
                    file=sys.stderr,
                )
                return 2

            restarted = client.restart(
                args.container,
                timeout_seconds=args.timeout,
            )

            result = {
                "container": restarted,
                "status": "RESTARTED",
            }

            if json_output:
                _print_json(
                    result,
                    pretty=args.pretty,
                )
            else:
                print(
                    f"Container restarted: {restarted}"
                )

            return 0

        if args.command == "info":
            result = client.server_info()

            if json_output:
                _print_json(
                    result,
                    pretty=args.pretty,
                )
            else:
                for key, value in result.items():
                    label = key.replace(
                        "_",
                        " ",
                    ).title()

                    print(
                        f"{label:<22}: {value}"
                    )

            return (
                0
                if result.get("available")
                else 1
            )

        parser.error(
            f"Unsupported command: {args.command}"
        )

    except (
        CommandExecutionError,
        ValidationError,
        ValueError,
        KeyError,
    ) as exc:
        if json_output:
            _print_json(
                {
                    "error": exc.__class__.__name__,
                    "message": str(exc),
                },
                pretty=args.pretty,
            )
        else:
            print(
                f"ERROR: {exc}",
                file=sys.stderr,
            )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
