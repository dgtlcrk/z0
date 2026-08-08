"""Unified CLI for z0_n3t platform capabilities."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

from z0.adapters.registry import build_adapter_registry
from z0.api.server import serve
from z0.api.snapshot import build_snapshot
from z0.botops.render import render_banner
from z0.config import config
from z0.network import collect_network_status
from z0.network.gateway import collect_gateway_status
from z0.network.neighbors import collect_neighbors
from z0.plugins.registry import build_plugin_registry
from z0.scheduler.engine import Scheduler


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _print_adapters(records: list[dict[str, Any]]) -> None:
    if not records:
        print("No adapters configured.")
        return

    header = (
        f"{'NAME':<16} "
        f"{'STATE':<16} "
        f"{'ENABLED':<9} "
        f"{'CONNECTED':<11} "
        f"{'DETAIL'}"
    )

    print("Adapters")
    print(header)
    print("-" * len(header))

    for record in records:
        enabled = "YES" if record.get("enabled") else "NO"
        connected = "YES" if record.get("connected") else "NO"

        print(
            f"{str(record.get('name', '')):<16} "
            f"{str(record.get('state', '')):<16} "
            f"{enabled:<9} "
            f"{connected:<11} "
            f"{record.get('detail', '')}"
        )



def _print_plugins(records: list[dict[str, Any]]) -> None:
    if not records:
        print("No plugins discovered.")
        return

    header = (
        f"{'NAME':<16} "
        f"{'VERSION':<12} "
        f"{'ENABLED':<9} "
        f"{'DESCRIPTION'}"
    )

    print("Plugins")
    print(header)
    print("-" * len(header))

    for record in records:
        enabled = "YES" if record.get("enabled") else "NO"

        print(
            f"{str(record.get('name', '')):<16} "
            f"{str(record.get('version', '')):<12} "
            f"{enabled:<9} "
            f"{record.get('description', '')}"
        )


def _format_job_interval(seconds: Any) -> str:
    try:
        value = int(seconds)
    except (TypeError, ValueError):
        return str(seconds or "-")

    if value % 3600 == 0:
        return f"{value // 3600}h"

    if value % 60 == 0:
        return f"{value // 60}m"

    return f"{value}s"


def _format_job_time(value: Any) -> str:
    if not value:
        return "-"

    text = str(value)

    try:
        timestamp = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )
    except ValueError:
        return text

    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(
            timezone.utc
        )
        return timestamp.strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

    return timestamp.strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _print_jobs(records: list[dict[str, Any]]) -> None:
    print("Scheduler Jobs")
    print("-" * 68)

    if not records:
        print("No scheduler jobs configured.")
        return

    for index, record in enumerate(records):
        if index:
            print()

        enabled = "YES" if record.get("enabled") else "NO"

        print(record.get("name", "Unnamed job"))
        print(f"  Job ID    : {record.get('job_id', '-')}")
        print(f"  Plugin    : {record.get('plugin', '-')}")
        print(f"  Action    : {record.get('action', '-')}")
        print(f"  Enabled   : {enabled}")
        print(
            "  Interval  : "
            f"{_format_job_interval(record.get('interval_seconds'))}"
        )
        print(
            "  Status    : "
            f"{record.get('last_status') or 'PENDING'}"
        )
        print(
            "  Last Run  : "
            f"{_format_job_time(record.get('last_run'))}"
        )
        print(
            "  Next Run  : "
            f"{_format_job_time(record.get('next_run'))}"
        )

        if record.get("last_error"):
            print(f"  Last Error: {record['last_error']}")

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="z0-platform",
        description="z0_n3t automation platform CLI",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    status = subparsers.add_parser(
        "status",
        help="Display platform status",
    )
    status.add_argument(
        "--json",
        action="store_true",
        help="Output the complete JSON platform snapshot",
    )

    adapters = subparsers.add_parser(
        "adapters",
        help="List adapter status",
    )
    adapters.add_argument(
        "--connect",
        help="Attempt to connect a named adapter",
    )
    adapters.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON",
    )

    plugins = subparsers.add_parser(
        "plugins",
        help="List or execute plugins",
    )
    plugins.add_argument("--run")
    plugins.add_argument("--action", default="status")
    plugins.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON",
    )

    jobs = subparsers.add_parser(
        "jobs",
        help="Manage scheduler jobs",
    )
    jobs_sub = jobs.add_subparsers(
        dest="jobs_command",
        required=True,
    )

    list_jobs = jobs_sub.add_parser("list")
    list_jobs.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON",
    )

    add_job = jobs_sub.add_parser("add")
    add_job.add_argument("--name", required=True)
    add_job.add_argument("--plugin", required=True)
    add_job.add_argument("--action", required=True)
    add_job.add_argument(
        "--interval",
        required=True,
        type=int,
        help="Interval in seconds",
    )

    remove_job = jobs_sub.add_parser("remove")
    remove_job.add_argument("job_id")

    run_job = jobs_sub.add_parser("run")
    run_job.add_argument("job_id")

    jobs_sub.add_parser("run-due")

    daemon = jobs_sub.add_parser("daemon")
    daemon.add_argument("--poll", type=int, default=5)

    api = subparsers.add_parser(
        "api",
        help="Run the JSON HTTP API",
    )
    api.add_argument(
        "--host",
        default=config["api"]["host"],
    )
    api.add_argument(
        "--port",
        type=int,
        default=config["api"]["port"],
    )


    network = subparsers.add_parser(
        "network",
        help="Show network edge information",
    )

    network_sub = network.add_subparsers(
        dest="network_command",
        required=True,
    )

    network_status = network_sub.add_parser(
        "status",
        help="Show network status",
    )

    network_status.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON",
    )


    network_gateway = network_sub.add_parser(
        "gateway",
        help="Show Internet gateway status",
    )

    network_gateway.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON",
    )


    network_neighbors = network_sub.add_parser(
        "neighbors",
        help="Show kernel network neighbors",
    )

    network_neighbors.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "status":
        if args.json:
            _print_json(build_snapshot())
        else:
            print(
                render_banner(
                    include_welcome=False,
                )
            )

        return

    if args.command == "adapters":
        registry = build_adapter_registry()

        if args.connect:
            adapter = registry.get(args.connect)

            try:
                adapter.connect()
            except NotImplementedError as error:
                print(error)
            except RuntimeError as error:
                print(error)

        records = [
            status.to_dict()
            for status in registry.statuses()
        ]

        if args.json:
            _print_json(records)
        else:
            _print_adapters(records)

        return

    if args.command == "plugins":
        registry = build_plugin_registry()

        if args.run:
            _print_json(
                registry.execute(args.run, args.action)
            )
        else:
            records = [
                metadata.to_dict()
                for metadata in registry.metadata()
            ]

            if args.json:
                _print_json(records)
            else:
                _print_plugins(records)

        return

    if args.command == "jobs":
        scheduler = Scheduler()

        if args.jobs_command == "list":
            records = [
                job.to_dict()
                for job in scheduler.list_jobs()
            ]

            if args.json:
                _print_json(records)
            else:
                _print_jobs(records)
        elif args.jobs_command == "add":
            job = scheduler.add_job(
                name=args.name,
                plugin=args.plugin,
                action=args.action,
                interval_seconds=args.interval,
            )
            _print_json(job.to_dict())
        elif args.jobs_command == "remove":
            removed = scheduler.remove_job(args.job_id)
            _print_json({"removed": removed})
        elif args.jobs_command == "run":
            _print_json(
                scheduler.run_job_by_id(args.job_id)
            )
        elif args.jobs_command == "run-due":
            _print_json(scheduler.run_due())
        elif args.jobs_command == "daemon":
            scheduler.serve_forever(args.poll)

        return

    if args.command == "network":
        if args.network_command == "status":
            record = collect_network_status().to_dict()

            if args.json:
                _print_json(record)
            else:
                print("Network")
                print("-" * 60)
                print(f"Interface       : {record['interface']}")
                print(f"IPv4 Address    : {record['ipv4_address']}")
                print(f"Network         : {record['network']}")
                print(f"Gateway         : {record['gateway']}")
                print(
                    "Gateway Status  : "
                    f"{'ONLINE' if record['gateway_reachable'] else 'OFFLINE'}"
                )
                print(f"DNS Server      : {record['dns_server']}")
                print(
                    "DNS             : "
                    f"{'HEALTHY' if record['dns_working'] else 'FAILED'}"
                )
                print(
                    "IPv4 Internet   : "
                    f"{'ONLINE' if record['ipv4_internet'] else 'OFFLINE'}"
                )
                print(
                    "IPv6            : "
                    f"{'AVAILABLE' if record['ipv6_available'] else 'UNAVAILABLE'}"
                )

        elif args.network_command == "gateway":
            record = collect_gateway_status().to_dict()

            if args.json:
                _print_json(record)
            else:
                print("Internet Gateway")
                print("-" * 60)
                print(f"Address         : {record['gateway']}")
                print(
                    "Status          : "
                    f"{'ONLINE' if record['reachable'] else 'OFFLINE'}"
                )
                print(f"Manufacturer    : {record['manufacturer']}")
                print(f"Model           : {record['model']}")
                print(f"Software        : {record['software_version']}")
                print(f"Hardware        : {record['hardware_version']}")
                print()
                print("WAN")
                print("-" * 60)
                print(f"Source          : {record['wan_source']}")
                print(f"Connection      : {record['wan_status']}")
                print(f"Network Type    : {record['network_type']}")
                print(f"Public IPv4     : {record['public_ipv4']}")
                print(f"Upstream GW     : {record['upstream_gateway']}")
                print(f"Primary DNS     : {record['primary_dns']}")
                print(f"Secondary DNS   : {record['secondary_dns']}")
                print(f"MTU             : {record['mtu']}")
                print()
                print("Health")
                print("-" * 60)
                print(f"RX Drops        : {record['receive_drops']}")
                print(f"TX Drops        : {record['transmit_drops']}")
                print(f"RX Errors       : {record['receive_errors']}")
                print(f"TX Errors       : {record['transmit_errors']}")
                print(f"PON Status      : {record['pon_status']}")
                print(f"UNI Status      : {record['uni_status']}")

        elif args.network_command == "neighbors":
            records = [
                neighbor.to_dict()
                for neighbor in collect_neighbors()
            ]

            if args.json:
                _print_json(records)
            else:
                print("Network Neighbors")
                print(
                    f"{'IP ADDRESS':<42} "
                    f"{'MAC ADDRESS':<18} "
                    f"{'INTERFACE':<10} "
                    f"{'STATE'}"
                )
                print("-" * 88)

                if not records:
                    print("No network neighbors found.")
                else:
                    for record in records:
                        print(
                            f"{record['ip_address']:<42} "
                            f"{record['mac_address']:<18} "
                            f"{record['interface']:<10} "
                            f"{record['state']}"
                        )

        return

    if args.command == "api":
        serve(args.host, args.port)
        return

    parser.error("Unsupported command")


if __name__ == "__main__":
    main()
