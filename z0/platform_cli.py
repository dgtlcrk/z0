"""Unified CLI for z0_n3t platform capabilities."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from z0.adapters.registry import build_adapter_registry
from z0.api.server import serve
from z0.api.snapshot import build_snapshot
from z0.botops.render import render_banner
from z0.config import config
from z0.network import collect_network_status
from z0.network.devices import collect_devices
from z0.network.discovery import discover_hosts
from z0.network.gateway import collect_gateway_status
from z0.network.gateway_devices import collect_gateway_devices
from z0.network.inventory import inventory_devices, update_inventory
from z0.network.neighbors import collect_neighbors
from z0.network.state_intelligence import assess_states
from z0.network.tracked_inventory import load_tracked, update_tracked
from z0.network.unified import collect_unified_devices
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


    gateway_devices = network_sub.add_parser(
        "gateway-devices",
        help="Read BGW320 LAN-side device records",
    )
    gateway_devices.add_argument(
        "--json", action="store_true", help="Output structured JSON"
    )
    gateway_devices.add_argument(
        "--html-file", type=Path, help="Parse a saved BGW320 devices page"
    )

    network_unified = network_sub.add_parser(
        "unified", help="Read combined gateway and LAN observations"
    )
    network_unified.add_argument("--json", action="store_true")

    network_neighbors = network_sub.add_parser(
        "neighbors",
        help="Show kernel network neighbors",
    )

    network_neighbors.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON",
    )


    network_devices = network_sub.add_parser(
        "devices",
        help="Show normalized LAN device inventory",
    )

    network_devices.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON",
    )


    network_discover = network_sub.add_parser(
        "discover",
        help="Actively discover reachable LAN hosts",
    )

    network_discover.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON",
    )


    inventory = subparsers.add_parser(
        "inventory",
        help="Manage persistent network inventory",
    )

    inventory_sub = inventory.add_subparsers(
        dest="inventory_command",
        required=True,
    )

    inventory_list = inventory_sub.add_parser(
        "list",
        help="List persistent network inventory",
    )

    inventory_list.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON",
    )

    inventory_update = inventory_sub.add_parser(
        "update",
        help="Refresh persistent network inventory",
    )

    inventory_update.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON",
    )

    tracked_list = inventory_sub.add_parser(
        "unified-list", help="List version-2 unified inventory"
    )
    tracked_list.add_argument("--json", action="store_true")

    tracked_update = inventory_sub.add_parser(
        "unified-update", help="Persist version-2 unified observations"
    )
    tracked_update.add_argument("--json", action="store_true")

    assess = inventory_sub.add_parser(
        "assess", help="Assess v2 device states without scanning or writing"
    )
    assess.add_argument("--json", action="store_true")
    assess.add_argument(
        "--stale-hours", type=float, default=24,
        help=(
            "Hours since last observation before a previously online "
            "missing device becomes SUSPECT"
        ),
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

        elif args.network_command == "gateway-devices":
            try:
                records = [
                    device.to_dict()
                    for device in collect_gateway_devices(html_file=args.html_file)
                ]
            except (OSError, TimeoutError) as error:
                parser.exit(1, f"Unable to read BGW320 device page: {error}\n")
            if args.json:
                _print_json(records)
            else:
                print("BGW320 LAN Devices")
                print(
                    f"{'IP ADDRESS':<16} {'NAME':<30} "
                    f"{'MAC ADDRESS':<18} {'STATUS':<8} {'CONNECTION'}"
                )
                print("-" * 105)
                for record in records:
                    print(
                        f"{record['ipv4_address']:<16} "
                        f"{record['name'][:30]:<30} "
                        f"{record['mac_address']:<18} "
                        f"{record['status']:<8} "
                        f"{record['connection_type']}"
                    )
                print(f"Gateway records: {len(records)}")

        elif args.network_command == "unified":
            try:
                records = [
                    device.to_dict() for device in collect_unified_devices()
                ]
            except (OSError, TimeoutError) as error:
                parser.exit(1, f"Unable to collect unified LAN data: {error}\n")
            if args.json:
                _print_json(records)
            else:
                print("Unified LAN Observations (read-only)")
                print(
                    f"{'IP ADDRESS':<16} {'NAME':<25} {'MAC ADDRESS':<18} "
                    f"{'STATE':<12} {'GW':<5} {'SOURCES'}"
                )
                print("-" * 110)
                for record in records:
                    print(
                        f"{record['ip_address']:<16} "
                        f"{record['hostname'][:25]:<25} "
                        f"{record['mac_address']:<18} "
                        f"{record['state']:<12} "
                        f"{record['gateway_status']:<5} "
                        f"{','.join(record['sources'])}"
                    )
                print(f"Unified records: {len(records)}")

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

        elif args.network_command == "devices":
            records = [
                device.to_dict()
                for device in collect_devices()
            ]

            if args.json:
                _print_json(records)
            else:
                print("LAN Devices")
                print(
                    f"{'IP ADDRESS':<16} "
                    f"{'HOSTNAME':<24} "
                    f"{'MAC ADDRESS':<18} "
                    f"{'ROLE':<12} "
                    f"{'STATE':<10} "
                    f"{'SOURCE'}"
                )
                print("-" * 110)

                if not records:
                    print("No LAN devices found.")
                else:
                    for record in records:
                        print(
                            f"{record['ip_address']:<16} "
                            f"{record['hostname']:<24} "
                            f"{record['mac_address']:<18} "
                            f"{record['role']:<12} "
                            f"{record['state']:<10} "
                            f"{record['source']}"
                        )

        elif args.network_command == "discover":
            records = [
                host.to_dict()
                for host in discover_hosts()
            ]

            if args.json:
                _print_json(records)
            else:
                print("LAN Discovery")
                print(
                    f"{'IP ADDRESS':<16} "
                    f"{'HOSTNAME':<30} "
                    f"{'MAC ADDRESS':<18} "
                    f"{'INTERFACE':<10} "
                    f"{'SOURCE'}"
                )
                print("-" * 100)

                if not records:
                    print("No reachable LAN hosts found.")
                else:
                    for record in records:
                        print(
                            f"{record['ip_address']:<16} "
                            f"{record['hostname']:<30} "
                            f"{record['mac_address']:<18} "
                            f"{record['interface']:<10} "
                            f"{record['source']}"
                        )

                print()
                print(f"Reachable hosts: {len(records)}")

        return

    if args.command == "inventory" and args.inventory_command == "assess":
        try:
            records = [
                item.to_dict()
                for item in assess_states(
                    load_tracked(), stale_hours=args.stale_hours
                )
            ]
        except (OSError, ValueError, TypeError, KeyError) as error:
            parser.exit(1, f"Inventory assessment failed: {error}\n")
        if args.json:
            _print_json(records)
        else:
            print(f"Read-only device state assessment: {len(records)} device(s)")
            print(
                f"{'IP ADDRESS':<16} {'ASSESSMENT':<20} "
                f"{'OBSERVED':<15} {'DEVICE'}"
            )
            for record in records:
                print(
                    f"{record['ip_address']:<16} "
                    f"{record['assessment']:<20} "
                    f"{record['observed_state']:<15} "
                    f"{record['hostname'] or record['identity']}"
                )
        return

    if args.command == "inventory" and args.inventory_command in {
        "unified-list", "unified-update"
    }:
        try:
            inventory = (
                update_tracked()
                if args.inventory_command == "unified-update"
                else load_tracked()
            )
        except (OSError, ValueError, TypeError, KeyError) as error:
            parser.exit(1, f"Unified inventory failed: {error}\n")
        records = [item.to_dict() for item in inventory.values()]
        if args.json:
            _print_json(records)
        else:
            action = (
                "updated" if args.inventory_command == "unified-update"
                else "loaded"
            )
            print(f"Unified inventory {action}: {len(records)} device(s)")
            for item in inventory.values():
                print(
                    f"{item.ip_address:<16} {item.mac_address:<18} "
                    f"{item.state:<14} {item.hostname}"
                )
        return

    if args.command == "inventory":
        if args.inventory_command == "update":
            inventory = update_inventory()

            records = [
                device.to_dict()
                for device in inventory.values()
            ]

            if args.json:
                _print_json(records)
            else:
                print(
                    f"Inventory updated: "
                    f"{len(records)} device(s)"
                )

        elif args.inventory_command == "list":
            records = [
                device.to_dict()
                for device in inventory_devices()
            ]

            if args.json:
                _print_json(records)
            else:
                print("Network Inventory")
                print(
                    f"{'IP ADDRESS':<16} "
                    f"{'HOSTNAME':<30} "
                    f"{'ROLE':<12} "
                    f"{'STATE':<10} "
                    f"{'FIRST SEEN':<27} "
                    f"{'LAST SEEN'}"
                )
                print("-" * 125)

                if not records:
                    print("Inventory is empty.")
                else:
                    for record in records:
                        print(
                            f"{record['ip_address']:<16} "
                            f"{record['hostname'][:30]:<30} "
                            f"{record['role']:<12} "
                            f"{record['state']:<10} "
                            f"{record['first_seen']:<27} "
                            f"{record['last_seen']}"
                        )

        return

    if args.command == "api":
        serve(args.host, args.port)
        return

    parser.error("Unsupported command")


if __name__ == "__main__":
    main()
