"""Unified CLI for z0_n3t platform capabilities."""

from __future__ import annotations

import argparse
import json
from typing import Any

from z0.adapters.registry import build_adapter_registry
from z0.api.server import serve
from z0.config import config
from z0.api.snapshot import build_snapshot
from z0.plugins.registry import build_plugin_registry
from z0.scheduler.engine import Scheduler


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="z0-platform",
        description="z0_n3t automation platform CLI",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "status",
        help="Display a complete JSON platform snapshot",
    )

    adapters = subparsers.add_parser(
        "adapters",
        help="List adapter status",
    )
    adapters.add_argument(
        "--connect",
        help="Attempt to connect a named adapter",
    )

    plugins = subparsers.add_parser(
        "plugins",
        help="List or execute plugins",
    )
    plugins.add_argument("--run")
    plugins.add_argument("--action", default="status")

    jobs = subparsers.add_parser(
        "jobs",
        help="Manage scheduler jobs",
    )
    jobs_sub = jobs.add_subparsers(
        dest="jobs_command",
        required=True,
    )

    jobs_sub.add_parser("list")

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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "status":
        _print_json(build_snapshot())
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

        _print_json(
            [status.to_dict() for status in registry.statuses()]
        )
        return

    if args.command == "plugins":
        registry = build_plugin_registry()

        if args.run:
            _print_json(
                registry.execute(args.run, args.action)
            )
        else:
            _print_json(
                [
                    metadata.to_dict()
                    for metadata in registry.metadata()
                ]
            )
        return

    if args.command == "jobs":
        scheduler = Scheduler()

        if args.jobs_command == "list":
            _print_json(
                [job.to_dict() for job in scheduler.list_jobs()]
            )
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

    if args.command == "api":
        serve(args.host, args.port)
        return

    parser.error("Unsupported command")


if __name__ == "__main__":
    main()
