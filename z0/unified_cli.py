"""Unified command dispatcher for the z0 platform."""

from __future__ import annotations

import sys
from collections.abc import Sequence


def _print_help() -> None:
    print(
        """z0_n3t operations platform

Usage:
  z0 status
  z0 adapters
  z0 plugins
  z0 jobs
  z0 api
  z0 docker <command>

Docker commands:
  z0 docker status
  z0 docker ps
  z0 docker ps --all
  z0 docker info
  z0 docker inspect CONTAINER
  z0 docker stats [CONTAINER ...]
  z0 docker logs CONTAINER
  z0 docker restart CONTAINER

Examples:
  z0 docker status
  z0 docker ps --all
  z0 docker stats jenkins
  z0 docker logs jenkins --tail 50
"""
    )


def main(
    argv: Sequence[str] | None = None,
) -> int:
    arguments = list(
        sys.argv[1:]
        if argv is None
        else argv
    )

    if not arguments:
        _print_help()
        return 0

    if arguments[0] in {
        "-h",
        "--help",
        "help",
    }:
        _print_help()
        return 0

    if arguments[0] == "docker":
        from z0.docker_cli import main as docker_main

        return docker_main(
            arguments[1:]
        )

    try:
        from z0.platform_cli import main as platform_main
    except ImportError as exc:
        print(
            f"Unable to load z0 platform CLI: {exc}",
            file=sys.stderr,
        )
        return 1

    original_argv = sys.argv[:]

    try:
        sys.argv = [
            original_argv[0],
            *arguments,
        ]

        result = platform_main()
    finally:
        sys.argv = original_argv

    if isinstance(result, int):
        return result

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
