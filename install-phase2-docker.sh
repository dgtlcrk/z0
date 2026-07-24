#!/usr/bin/env bash
#
# z0 Phase 2
#
# Adds:
#   - Docker operations client
#   - Docker inventory and health
#   - Container inspect, stats, logs, and restart
#   - Docker plugin
#   - Unified `z0 docker ...` CLI
#   - `/api/docker` API endpoints
#   - Unit and API tests
#
# Jenkins remains separate and untouched.
#

set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

on_error() {
    local exit_code=$?
    local line_number="${1:-unknown}"

    echo
    echo "ERROR: ${SCRIPT_NAME} failed at line ${line_number}"
    echo "Exit code: ${exit_code}"
    exit "${exit_code}"
}

trap 'on_error $LINENO' ERR

log() {
    echo
    echo "[$(date -u +%H:%M:%S)] $*"
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

if [[ "$(id -u)" -eq 0 ]]; then
    die "Do not run this installer with sudo."
fi

command -v git >/dev/null 2>&1 ||
    die "Git is required."

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" ||
    die "Run this script inside the z0 Git repository."

cd "${REPO_ROOT}"

[[ -f pyproject.toml ]] ||
    die "pyproject.toml was not found."

[[ -d z0 ]] ||
    die "The z0 Python package was not found."

[[ -x .venv/bin/python ]] ||
    die "The project virtual environment was not found at .venv."

PYTHON="${REPO_ROOT}/.venv/bin/python"
BACKUP_DIR="${REPO_ROOT}/.z0-backups/phase2-docker/${TIMESTAMP}"

TARGET_FILES=(
    "pyproject.toml"
    "z0/api/server.py"
    "z0/unified_cli.py"
    "z0/docker_cli.py"
    "z0/dockerops/__init__.py"
    "z0/dockerops/client.py"
    "z0/dockerops/models.py"
    "z0/plugins/builtin/docker.py"
    "tests/test_dockerops.py"
)

log "Repository: ${REPO_ROOT}"
log "Python: ${PYTHON}"

"${PYTHON}" - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit(
        f"Python 3.10 or newer is required. "
        f"Found {sys.version.split()[0]}"
    )

print(f"Python {sys.version.split()[0]} verified")
PY

BACKUP_CREATED=0

for relative_path in "${TARGET_FILES[@]}"; do
    if [[ -e "${REPO_ROOT}/${relative_path}" ]]; then
        mkdir -p "${BACKUP_DIR}/$(dirname "${relative_path}")"

        cp -a \
            "${REPO_ROOT}/${relative_path}" \
            "${BACKUP_DIR}/${relative_path}"

        BACKUP_CREATED=1
    fi
done

if [[ "${BACKUP_CREATED}" -eq 1 ]]; then
    log "Existing target files backed up to:"
    echo "  ${BACKUP_DIR}"
fi

mkdir -p \
    z0/dockerops \
    z0/plugins/builtin \
    z0/api \
    tests

log "Creating Docker data models"

cat > z0/dockerops/models.py <<'PY'
"""Docker data models used by the z0 operations platform."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DockerAvailability:
    """Docker engine availability result."""

    available: bool
    version: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ContainerSummary:
    """Summary of a Docker container."""

    container_id: str
    name: str
    image: str
    state: str
    status: str
    health: str
    ports: str
    created_at: str
    labels: str = ""

    @property
    def running(self) -> bool:
        return self.state.lower() == "running"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["running"] = self.running
        return payload


@dataclass(frozen=True, slots=True)
class ContainerStats:
    """Point-in-time Docker container resource statistics."""

    container_id: str
    name: str
    cpu_percent: str
    memory_usage: str
    memory_percent: str
    network_io: str
    block_io: str
    pids: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DockerSummary:
    """Docker engine and container summary."""

    available: bool
    version: str
    detail: str
    total: int
    running: int
    stopped: int
    unhealthy: int
    containers: list[ContainerSummary] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "version": self.version,
            "detail": self.detail,
            "total": self.total,
            "running": self.running,
            "stopped": self.stopped,
            "unhealthy": self.unhealthy,
            "containers": [
                container.to_dict()
                for container in self.containers
            ],
        }
PY

log "Creating Docker operations client"

cat > z0/dockerops/client.py <<'PY'
"""Docker CLI-backed operations client."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from typing import Any

from z0.core import (
    CommandExecutionError,
    CommandResult,
    ValidationError,
    run_command,
    validate_positive_int,
)

from .models import (
    ContainerStats,
    ContainerSummary,
    DockerAvailability,
    DockerSummary,
)


CommandRunner = Callable[..., CommandResult]

_CONTAINER_REFERENCE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.:/@-]{0,254}$"
)


class DockerClient:
    """
    Docker operations client.

    The Docker command-line client is used instead of requiring the external
    Docker Python SDK. This keeps the z0 core lightweight and works with the
    Docker installation already present on the Raspberry Pi.
    """

    def __init__(
        self,
        *,
        runner: CommandRunner = run_command,
        timeout: float = 30,
    ) -> None:
        self._runner = runner
        self.timeout = timeout

    def _run(
        self,
        arguments: Sequence[str],
        *,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        command = ["docker", *arguments]

        return self._runner(
            command,
            timeout=self.timeout if timeout is None else timeout,
            check=check,
        )

    @staticmethod
    def _validate_container_reference(value: str) -> str:
        reference = value.strip()

        if not reference:
            raise ValidationError(
                "A container name or ID is required"
            )

        if not _CONTAINER_REFERENCE.fullmatch(reference):
            raise ValidationError(
                f"Invalid Docker container reference: {value!r}"
            )

        return reference

    @staticmethod
    def _parse_json_lines(content: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        for line_number, raw_line in enumerate(
            content.splitlines(),
            start=1,
        ):
            line = raw_line.strip()

            if not line:
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Docker returned invalid JSON on line "
                    f"{line_number}: {exc.msg}"
                ) from exc

            if isinstance(value, dict):
                records.append(value)

        return records

    @staticmethod
    def _health_from_status(status: str) -> str:
        normalized = status.lower()

        if "(unhealthy)" in normalized:
            return "UNHEALTHY"

        if "(healthy)" in normalized:
            return "HEALTHY"

        if "(health: starting)" in normalized:
            return "STARTING"

        return "NONE"

    def availability(self) -> DockerAvailability:
        """Check whether the Docker engine is reachable."""

        result = self._run(
            [
                "version",
                "--format",
                "{{.Server.Version}}",
            ],
            check=False,
        )

        if result.returncode != 0:
            detail = (
                result.stderr.strip()
                or result.stdout.strip()
                or "Docker engine is not reachable"
            )

            return DockerAvailability(
                available=False,
                detail=detail,
            )

        return DockerAvailability(
            available=True,
            version=result.stdout.strip(),
            detail="Docker engine is reachable",
        )

    def server_info(self) -> dict[str, Any]:
        """Return selected Docker engine information."""

        availability = self.availability()

        if not availability.available:
            return {
                "available": False,
                "version": "",
                "detail": availability.detail,
            }

        result = self._run(
            [
                "info",
                "--format",
                "{{json .}}",
            ]
        )

        try:
            raw_info = json.loads(result.stdout)
        except json.JSONDecodeError:
            raw_info = {}

        if not isinstance(raw_info, dict):
            raw_info = {}

        return {
            "available": True,
            "version": availability.version,
            "detail": availability.detail,
            "server_version": raw_info.get(
                "ServerVersion",
                availability.version,
            ),
            "operating_system": raw_info.get(
                "OperatingSystem",
                "",
            ),
            "architecture": raw_info.get(
                "Architecture",
                "",
            ),
            "kernel_version": raw_info.get(
                "KernelVersion",
                "",
            ),
            "containers": raw_info.get(
                "Containers",
                0,
            ),
            "containers_running": raw_info.get(
                "ContainersRunning",
                0,
            ),
            "containers_paused": raw_info.get(
                "ContainersPaused",
                0,
            ),
            "containers_stopped": raw_info.get(
                "ContainersStopped",
                0,
            ),
            "images": raw_info.get(
                "Images",
                0,
            ),
            "docker_root_dir": raw_info.get(
                "DockerRootDir",
                "",
            ),
        }

    def list_containers(
        self,
        *,
        all_containers: bool = True,
    ) -> list[ContainerSummary]:
        """List Docker containers."""

        arguments = ["ps"]

        if all_containers:
            arguments.append("--all")

        arguments.extend(
            [
                "--format",
                "{{json .}}",
            ]
        )

        result = self._run(arguments)
        records = self._parse_json_lines(result.stdout)

        containers: list[ContainerSummary] = []

        for record in records:
            status = str(record.get("Status", ""))

            containers.append(
                ContainerSummary(
                    container_id=str(
                        record.get("ID", "")
                    ),
                    name=str(
                        record.get("Names", "")
                    ),
                    image=str(
                        record.get("Image", "")
                    ),
                    state=str(
                        record.get("State", "")
                    ).upper(),
                    status=status,
                    health=self._health_from_status(status),
                    ports=str(
                        record.get("Ports", "")
                    ),
                    created_at=str(
                        record.get("CreatedAt", "")
                    ),
                    labels=str(
                        record.get("Labels", "")
                    ),
                )
            )

        return containers

    def summary(
        self,
        *,
        include_containers: bool = True,
    ) -> DockerSummary:
        """Return Docker engine and container status."""

        availability = self.availability()

        if not availability.available:
            return DockerSummary(
                available=False,
                version="",
                detail=availability.detail,
                total=0,
                running=0,
                stopped=0,
                unhealthy=0,
                containers=[],
            )

        containers = self.list_containers(
            all_containers=True
        )

        running = sum(
            1
            for container in containers
            if container.running
        )

        unhealthy = sum(
            1
            for container in containers
            if container.health == "UNHEALTHY"
        )

        return DockerSummary(
            available=True,
            version=availability.version,
            detail=availability.detail,
            total=len(containers),
            running=running,
            stopped=len(containers) - running,
            unhealthy=unhealthy,
            containers=(
                containers
                if include_containers
                else []
            ),
        )

    def inspect(self, container: str) -> dict[str, Any]:
        """Inspect one container."""

        reference = self._validate_container_reference(
            container
        )

        result = self._run(
            [
                "inspect",
                reference,
            ]
        )

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Docker inspect returned invalid JSON"
            ) from exc

        if not isinstance(payload, list) or not payload:
            raise ValueError(
                f"No inspection data returned for {reference}"
            )

        record = payload[0]

        if not isinstance(record, dict):
            raise ValueError(
                f"Unexpected inspection data for {reference}"
            )

        state = record.get("State", {})
        config = record.get("Config", {})
        network_settings = record.get(
            "NetworkSettings",
            {},
        )

        if not isinstance(state, dict):
            state = {}

        if not isinstance(config, dict):
            config = {}

        if not isinstance(network_settings, dict):
            network_settings = {}

        return {
            "id": record.get("Id", ""),
            "name": str(
                record.get("Name", "")
            ).lstrip("/"),
            "created": record.get("Created", ""),
            "path": record.get("Path", ""),
            "arguments": record.get("Args", []),
            "image": config.get("Image", ""),
            "hostname": config.get("Hostname", ""),
            "state": state,
            "restart_count": record.get(
                "RestartCount",
                0,
            ),
            "platform": record.get(
                "Platform",
                "",
            ),
            "driver": record.get(
                "Driver",
                "",
            ),
            "network_mode": record.get(
                "HostConfig",
                {},
            ).get(
                "NetworkMode",
                "",
            ),
            "ports": network_settings.get(
                "Ports",
                {},
            ),
            "networks": network_settings.get(
                "Networks",
                {},
            ),
            "mounts": record.get(
                "Mounts",
                [],
            ),
            "labels": config.get(
                "Labels",
                {},
            )
            or {},
        }

    def stats(
        self,
        containers: Sequence[str] | None = None,
    ) -> list[ContainerStats]:
        """Return a point-in-time Docker stats snapshot."""

        arguments = [
            "stats",
            "--no-stream",
            "--format",
            "{{json .}}",
        ]

        if containers:
            arguments.extend(
                self._validate_container_reference(container)
                for container in containers
            )

        result = self._run(
            arguments,
            timeout=60,
        )

        records = self._parse_json_lines(
            result.stdout
        )

        statistics: list[ContainerStats] = []

        for record in records:
            statistics.append(
                ContainerStats(
                    container_id=str(
                        record.get(
                            "ID",
                            record.get(
                                "Container",
                                "",
                            ),
                        )
                    ),
                    name=str(
                        record.get("Name", "")
                    ),
                    cpu_percent=str(
                        record.get("CPUPerc", "")
                    ),
                    memory_usage=str(
                        record.get("MemUsage", "")
                    ),
                    memory_percent=str(
                        record.get("MemPerc", "")
                    ),
                    network_io=str(
                        record.get("NetIO", "")
                    ),
                    block_io=str(
                        record.get("BlockIO", "")
                    ),
                    pids=str(
                        record.get("PIDs", "")
                    ),
                )
            )

        return statistics

    def logs(
        self,
        container: str,
        *,
        tail: int = 100,
        timestamps: bool = False,
    ) -> str:
        """Return recent container logs."""

        reference = self._validate_container_reference(
            container
        )
        validated_tail = validate_positive_int(
            tail,
            name="tail",
        )

        arguments = [
            "logs",
            "--tail",
            str(validated_tail),
        ]

        if timestamps:
            arguments.append("--timestamps")

        arguments.append(reference)

        result = self._run(
            arguments,
            timeout=60,
        )

        if result.stdout and result.stderr:
            return (
                result.stdout.rstrip()
                + "\n"
                + result.stderr.rstrip()
            ).strip()

        return (
            result.stdout
            or result.stderr
        ).rstrip()

    def restart(
        self,
        container: str,
        *,
        timeout_seconds: int = 10,
    ) -> str:
        """Restart a Docker container."""

        reference = self._validate_container_reference(
            container
        )
        validated_timeout = validate_positive_int(
            timeout_seconds,
            name="timeout_seconds",
            allow_zero=True,
        )

        result = self._run(
            [
                "restart",
                "--time",
                str(validated_timeout),
                reference,
            ],
            timeout=max(
                60,
                validated_timeout + 30,
            ),
        )

        return result.stdout.strip() or reference


def docker_error_payload(
    exc: Exception,
) -> dict[str, Any]:
    """Convert an expected Docker failure to API-safe data."""

    if isinstance(exc, CommandExecutionError):
        return {
            "error": "docker_command_failed",
            "message": str(exc),
            "command": exc.command,
            "returncode": exc.returncode,
            "stderr": exc.stderr.strip(),
        }

    return {
        "error": exc.__class__.__name__,
        "message": str(exc),
    }
PY

log "Creating Docker package exports"

cat > z0/dockerops/__init__.py <<'PY'
"""Docker operations for the z0 platform."""

from .client import (
    DockerClient,
    docker_error_payload,
)
from .models import (
    ContainerStats,
    ContainerSummary,
    DockerAvailability,
    DockerSummary,
)

__all__ = [
    "ContainerStats",
    "ContainerSummary",
    "DockerAvailability",
    "DockerClient",
    "DockerSummary",
    "docker_error_payload",
]
PY

log "Creating Docker plugin"

cat > z0/plugins/builtin/docker.py <<'PY'
"""Built-in Docker operations plugin."""

from __future__ import annotations

from typing import Any

from z0.dockerops import DockerClient


class DockerPlugin:
    """Docker monitoring and container operations plugin."""

    name = "docker"
    version = "1.0.0"
    description = (
        "Monitor Docker and perform controlled container operations"
    )
    enabled = True

    def __init__(
        self,
        client: DockerClient | None = None,
    ) -> None:
        self.client = client or DockerClient()

    def to_dict(self) -> dict[str, Any]:
        availability = self.client.availability()

        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "enabled": self.enabled,
            "available": availability.available,
            "detail": availability.detail,
        }

    def execute(
        self,
        action: str = "summary",
        **kwargs: Any,
    ) -> Any:
        """Execute a Docker plugin action."""

        normalized = action.strip().lower()

        if normalized in {"summary", "status"}:
            return self.client.summary().to_dict()

        if normalized in {"ps", "containers"}:
            return [
                container.to_dict()
                for container in self.client.list_containers(
                    all_containers=bool(
                        kwargs.get(
                            "all_containers",
                            True,
                        )
                    )
                )
            ]

        if normalized == "inspect":
            return self.client.inspect(
                str(kwargs["container"])
            )

        if normalized == "stats":
            containers = kwargs.get("containers")

            return [
                statistics.to_dict()
                for statistics in self.client.stats(
                    containers
                )
            ]

        if normalized == "logs":
            return {
                "container": str(
                    kwargs["container"]
                ),
                "logs": self.client.logs(
                    str(kwargs["container"]),
                    tail=int(
                        kwargs.get("tail", 100)
                    ),
                    timestamps=bool(
                        kwargs.get(
                            "timestamps",
                            False,
                        )
                    ),
                ),
            }

        if normalized == "restart":
            return {
                "container": self.client.restart(
                    str(kwargs["container"]),
                    timeout_seconds=int(
                        kwargs.get(
                            "timeout_seconds",
                            10,
                        )
                    ),
                ),
                "status": "RESTARTED",
            }

        raise ValueError(
            f"Unsupported Docker plugin action: {action}"
        )

    def run(
        self,
        action: str = "summary",
        **kwargs: Any,
    ) -> Any:
        """Compatibility alias for plugin execution."""

        return self.execute(
            action,
            **kwargs,
        )


PLUGIN = DockerPlugin
PY

log "Creating Docker CLI"

cat > z0/docker_cli.py <<'PY'
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
PY

log "Creating unified z0 CLI dispatcher"

cat > z0/unified_cli.py <<'PY'
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
PY

log "Creating z0 API v1.1 with Docker endpoints"

cat > z0/api/server.py <<'PY'
"""HTTP API server for the z0 operations platform."""

from __future__ import annotations

import inspect
import json
import logging
from http import HTTPStatus
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from typing import Any
from urllib.parse import (
    parse_qs,
    urlparse,
)

from z0.core import (
    PlatformSettings,
    to_jsonable,
)
from z0.dockerops import (
    DockerClient,
    docker_error_payload,
)


LOGGER = logging.getLogger("z0.api")

API_ENDPOINTS = [
    "/api/status",
    "/api/system",
    "/api/inventory",
    "/api/services",
    "/api/health",
    "/api/adapters",
    "/api/plugins",
    "/api/jobs",
    "/api/project",
    "/api/docker",
    "/api/docker/info",
    "/api/docker/inspect?container=NAME",
    "/api/docker/stats",
    "/api/docker/logs?container=NAME&tail=100",
]


def _call_snapshot_function(
    function: Any,
) -> dict[str, Any] | None:
    if not callable(function):
        return None

    try:
        signature = inspect.signature(
            function
        )
    except (
        TypeError,
        ValueError,
    ):
        signature = None

    if signature is not None:
        required_parameters = [
            parameter
            for parameter in signature.parameters.values()
            if (
                parameter.default
                is inspect.Parameter.empty
                and parameter.kind
                in {
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                }
            )
        ]

        if required_parameters:
            return None

    result = function()

    if isinstance(result, dict):
        return result

    if hasattr(result, "to_dict"):
        converted = result.to_dict()

        if isinstance(converted, dict):
            return converted

    return None


def build_status_snapshot() -> dict[str, Any]:
    """
    Load the existing z0 platform snapshot.

    The loader supports several function names so it remains compatible with
    earlier z0 API snapshot implementations.
    """

    snapshot: dict[str, Any] | None = None
    errors: list[str] = []

    try:
        from z0.api import snapshot as snapshot_module
    except ImportError as exc:
        snapshot_module = None
        errors.append(str(exc))

    if snapshot_module is not None:
        candidate_names = (
            "build_snapshot",
            "get_snapshot",
            "collect_snapshot",
            "create_snapshot",
            "snapshot",
        )

        for candidate_name in candidate_names:
            candidate = getattr(
                snapshot_module,
                candidate_name,
                None,
            )

            try:
                snapshot = _call_snapshot_function(
                    candidate
                )
            except Exception as exc:
                errors.append(
                    f"{candidate_name}: {exc}"
                )
                continue

            if snapshot is not None:
                break

    if snapshot is None:
        settings = PlatformSettings.from_environment()

        snapshot = {
            "platform": {
                "name": settings.platform_name,
                "description": (
                    "Network Automation Platform"
                ),
            },
            "node": {
                "name": settings.node_name,
                "status": "ONLINE",
            },
        }

        if errors:
            snapshot["snapshot_warnings"] = errors

    try:
        snapshot["docker"] = (
            DockerClient()
            .summary()
            .to_dict()
        )
    except Exception as exc:
        snapshot["docker"] = (
            docker_error_payload(exc)
        )

    return snapshot


class Z0RequestHandler(
    BaseHTTPRequestHandler
):
    """Request handler for the z0 API."""

    server_version = "z0_n3t/1.1"
    protocol_version = "HTTP/1.1"

    def log_message(
        self,
        format_string: str,
        *arguments: Any,
    ) -> None:
        LOGGER.info(
            "%s - %s",
            self.address_string(),
            format_string % arguments,
        )

    def _send_json(
        self,
        payload: Any,
        *,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        encoded = json.dumps(
            to_jsonable(payload),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ).encode("utf-8")

        self.send_response(status.value)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(encoded)),
        )
        self.send_header(
            "Cache-Control",
            "no-store",
        )
        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )
        self.end_headers()

        try:
            self.wfile.write(encoded)
        except BrokenPipeError:
            return

    def _send_error_payload(
        self,
        status: HTTPStatus,
        message: str,
        **extra: Any,
    ) -> None:
        payload = {
            "error": status.phrase,
            "message": message,
            **extra,
        }

        self._send_json(
            payload,
            status=status,
        )

    @staticmethod
    def _first_query_value(
        query: dict[str, list[str]],
        key: str,
        default: str = "",
    ) -> str:
        values = query.get(key)

        if not values:
            return default

        return values[0]

    def _docker_request(
        self,
        path: str,
        query: dict[str, list[str]],
    ) -> None:
        client = DockerClient()

        try:
            if path == "/api/docker":
                include_value = (
                    self._first_query_value(
                        query,
                        "containers",
                        "true",
                    )
                    .strip()
                    .lower()
                )

                include_containers = (
                    include_value
                    not in {
                        "0",
                        "false",
                        "no",
                        "off",
                    }
                )

                payload = client.summary(
                    include_containers=include_containers
                ).to_dict()

                self._send_json(payload)
                return

            if path == "/api/docker/info":
                self._send_json(
                    client.server_info()
                )
                return

            if path == "/api/docker/inspect":
                container = (
                    self._first_query_value(
                        query,
                        "container",
                    )
                )

                if not container:
                    self._send_error_payload(
                        HTTPStatus.BAD_REQUEST,
                        "The container query parameter is required",
                    )
                    return

                self._send_json(
                    client.inspect(container)
                )
                return

            if path == "/api/docker/stats":
                containers = query.get(
                    "container",
                    [],
                )

                payload = [
                    statistics.to_dict()
                    for statistics in client.stats(
                        containers
                    )
                ]

                self._send_json(payload)
                return

            if path == "/api/docker/logs":
                container = (
                    self._first_query_value(
                        query,
                        "container",
                    )
                )

                if not container:
                    self._send_error_payload(
                        HTTPStatus.BAD_REQUEST,
                        "The container query parameter is required",
                    )
                    return

                tail_value = (
                    self._first_query_value(
                        query,
                        "tail",
                        "100",
                    )
                )

                try:
                    tail = int(tail_value)
                except ValueError:
                    self._send_error_payload(
                        HTTPStatus.BAD_REQUEST,
                        "The tail query parameter must be an integer",
                    )
                    return

                timestamps_value = (
                    self._first_query_value(
                        query,
                        "timestamps",
                        "false",
                    )
                    .strip()
                    .lower()
                )

                timestamps = timestamps_value in {
                    "1",
                    "true",
                    "yes",
                    "on",
                }

                self._send_json(
                    {
                        "container": container,
                        "tail": tail,
                        "timestamps": timestamps,
                        "logs": client.logs(
                            container,
                            tail=tail,
                            timestamps=timestamps,
                        ),
                    }
                )
                return

            self._send_error_payload(
                HTTPStatus.NOT_FOUND,
                f"Unknown Docker API endpoint: {path}",
            )

        except Exception as exc:
            payload = docker_error_payload(
                exc
            )

            self._send_json(
                payload,
                status=HTTPStatus.SERVICE_UNAVAILABLE,
            )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(
            parsed.query,
            keep_blank_values=True,
        )

        if path == "/":
            self._send_json(
                {
                    "service": "z0_n3t API",
                    "status": "ONLINE",
                    "version": "1.1",
                    "endpoints": API_ENDPOINTS,
                }
            )
            return

        if path.startswith("/api/docker"):
            self._docker_request(
                path,
                query,
            )
            return

        if path == "/api/status":
            self._send_json(
                build_status_snapshot()
            )
            return

        snapshot_key_map = {
            "/api/system": "system",
            "/api/inventory": "inventory",
            "/api/services": "services",
            "/api/health": "infrastructure",
            "/api/adapters": "adapters",
            "/api/plugins": "plugins",
            "/api/jobs": "jobs",
            "/api/project": "project",
        }

        snapshot_key = snapshot_key_map.get(
            path
        )

        if snapshot_key is not None:
            snapshot = build_status_snapshot()

            if snapshot_key not in snapshot:
                self._send_error_payload(
                    HTTPStatus.NOT_FOUND,
                    (
                        f"Snapshot section "
                        f"{snapshot_key!r} is unavailable"
                    ),
                )
                return

            self._send_json(
                snapshot[snapshot_key]
            )
            return

        self._send_error_payload(
            HTTPStatus.NOT_FOUND,
            f"Unknown API endpoint: {path}",
        )

    def do_POST(self) -> None:
        self._send_error_payload(
            HTTPStatus.METHOD_NOT_ALLOWED,
            (
                "The z0 Docker API is currently read-only. "
                "Use the local CLI for container restarts."
            ),
        )


RequestHandler = Z0RequestHandler
APIRequestHandler = Z0RequestHandler


def create_server(
    host: str = "127.0.0.1",
    port: int = 8081,
) -> ThreadingHTTPServer:
    """Create a z0 API server without starting it."""

    server = ThreadingHTTPServer(
        (host, port),
        Z0RequestHandler,
    )

    server.daemon_threads = True

    return server


def serve(
    host: str = "127.0.0.1",
    port: int = 8081,
) -> None:
    """Run the z0 API server."""

    server = create_server(
        host,
        port,
    )

    actual_host, actual_port = (
        server.server_address[:2]
    )

    print(
        f"z0_n3t API listening on "
        f"http://{actual_host}:{actual_port}"
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping z0_n3t API")
    finally:
        server.server_close()


def main() -> None:
    """Run the API using environment-based settings."""

    settings = PlatformSettings.from_environment()

    serve(
        settings.api_host,
        settings.api_port,
    )


if __name__ == "__main__":
    main()
PY

log "Updating Python console entry points"

"${PYTHON}" - <<'PYTHON'
from pathlib import Path
import re
import tomllib


path = Path("pyproject.toml")
text = path.read_text(encoding="utf-8")

# Refuse to modify an already-invalid project file.
tomllib.loads(text)

lines = text.splitlines()
section_header = "[project.scripts]"

try:
    section_start = next(
        index
        for index, line in enumerate(lines)
        if line.strip() == section_header
    )
except StopIteration:
    if lines and lines[-1].strip():
        lines.append("")

    lines.append(section_header)
    section_start = len(lines) - 1

section_end = len(lines)

for index in range(section_start + 1, len(lines)):
    stripped = lines[index].strip()

    if stripped.startswith("[") and stripped.endswith("]"):
        section_end = index
        break

desired_entries = {
    "z0": 'z0 = "z0.unified_cli:main"',
    "z0-docker": 'z0-docker = "z0.docker_cli:main"',
}

entry_pattern = re.compile(
    r"^\s*([A-Za-z0-9_.-]+)\s*="
)

existing_section = lines[
    section_start + 1:section_end
]

cleaned_section: list[str] = []

for line in existing_section:
    match = entry_pattern.match(line)

    if match and match.group(1) in desired_entries:
        continue

    cleaned_section.append(line)

while cleaned_section and not cleaned_section[-1].strip():
    cleaned_section.pop()

if cleaned_section:
    cleaned_section.append("")

cleaned_section.extend(desired_entries.values())
cleaned_section.append("")

updated_lines = (
    lines[:section_start + 1]
    + cleaned_section
    + lines[section_end:]
)

updated_text = "\n".join(updated_lines).rstrip() + "\n"

parsed = tomllib.loads(updated_text)
scripts = parsed.get("project", {}).get("scripts", {})

assert scripts.get("z0") == "z0.unified_cli:main"
assert scripts.get("z0-docker") == "z0.docker_cli:main"

path.write_text(
    updated_text,
    encoding="utf-8",
)

print("Console scripts configured safely:")
print(f"  z0        -> {scripts['z0']}")
print(f"  z0-docker -> {scripts['z0-docker']}")
PYTHON

log "Creating Docker operations tests"

cat > tests/test_dockerops.py <<'PY'
"""Tests for z0 Docker operations."""

from __future__ import annotations

import json
import threading
import unittest
from typing import Any
from unittest.mock import patch
from urllib.request import urlopen

from z0.core import CommandResult
from z0.dockerops import DockerClient


class FakeDockerRunner:
    """Deterministic Docker command runner for unit tests."""

    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def __call__(
        self,
        command: list[str],
        **kwargs: Any,
    ) -> CommandResult:
        recorded = tuple(command)
        self.commands.append(recorded)

        if command[:2] == [
            "docker",
            "version",
        ]:
            return CommandResult(
                command=recorded,
                returncode=0,
                stdout="29.6.2\n",
                stderr="",
            )

        if command[:2] == [
            "docker",
            "info",
        ]:
            payload = {
                "ServerVersion": "29.6.2",
                "OperatingSystem": "Ubuntu 24.04",
                "Architecture": "aarch64",
                "KernelVersion": "6.8.0",
                "Containers": 2,
                "ContainersRunning": 1,
                "ContainersPaused": 0,
                "ContainersStopped": 1,
                "Images": 3,
                "DockerRootDir": "/var/lib/docker",
            }

            return CommandResult(
                command=recorded,
                returncode=0,
                stdout=json.dumps(payload),
                stderr="",
            )

        if command[:2] == [
            "docker",
            "ps",
        ]:
            records = [
                {
                    "ID": "abc123",
                    "Names": "jenkins",
                    "Image": "jenkins/jenkins:lts",
                    "State": "running",
                    "Status": (
                        "Up 3 days (healthy)"
                    ),
                    "Ports": (
                        "0.0.0.0:8080->8080/tcp"
                    ),
                    "CreatedAt": (
                        "2026-07-20 10:00:00"
                    ),
                    "Labels": "",
                },
                {
                    "ID": "def456",
                    "Names": "test-stopped",
                    "Image": "alpine:latest",
                    "State": "exited",
                    "Status": "Exited (0) 1 hour ago",
                    "Ports": "",
                    "CreatedAt": (
                        "2026-07-23 08:00:00"
                    ),
                    "Labels": "",
                },
            ]

            return CommandResult(
                command=recorded,
                returncode=0,
                stdout="\n".join(
                    json.dumps(record)
                    for record in records
                ),
                stderr="",
            )

        if command[:2] == [
            "docker",
            "inspect",
        ]:
            payload = [
                {
                    "Id": "abc123",
                    "Name": "/jenkins",
                    "Created": (
                        "2026-07-20T10:00:00Z"
                    ),
                    "Path": "/usr/bin/tini",
                    "Args": ["--", "/usr/local/bin/jenkins.sh"],
                    "Config": {
                        "Image": "jenkins/jenkins:lts",
                        "Hostname": "abc123",
                        "Labels": {
                            "app": "jenkins",
                        },
                    },
                    "State": {
                        "Status": "running",
                        "Running": True,
                        "Health": {
                            "Status": "healthy",
                        },
                    },
                    "RestartCount": 0,
                    "Platform": "linux",
                    "Driver": "overlay2",
                    "HostConfig": {
                        "NetworkMode": "bridge",
                    },
                    "NetworkSettings": {
                        "Ports": {
                            "8080/tcp": [
                                {
                                    "HostPort": "8080",
                                }
                            ]
                        },
                        "Networks": {
                            "bridge": {
                                "IPAddress": "172.17.0.2",
                            }
                        },
                    },
                    "Mounts": [],
                }
            ]

            return CommandResult(
                command=recorded,
                returncode=0,
                stdout=json.dumps(payload),
                stderr="",
            )

        if command[:2] == [
            "docker",
            "stats",
        ]:
            payload = {
                "ID": "abc123",
                "Name": "jenkins",
                "CPUPerc": "1.25%",
                "MemUsage": (
                    "512MiB / 7.6GiB"
                ),
                "MemPerc": "6.58%",
                "NetIO": "1MB / 2MB",
                "BlockIO": "10MB / 4MB",
                "PIDs": "54",
            }

            return CommandResult(
                command=recorded,
                returncode=0,
                stdout=json.dumps(payload),
                stderr="",
            )

        if command[:2] == [
            "docker",
            "logs",
        ]:
            return CommandResult(
                command=recorded,
                returncode=0,
                stdout="Jenkins is fully up and running\n",
                stderr="",
            )

        if command[:2] == [
            "docker",
            "restart",
        ]:
            return CommandResult(
                command=recorded,
                returncode=0,
                stdout="jenkins\n",
                stderr="",
            )

        return CommandResult(
            command=recorded,
            returncode=1,
            stdout="",
            stderr=f"Unexpected command: {command}",
        )


class DockerClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = FakeDockerRunner()
        self.client = DockerClient(
            runner=self.runner
        )

    def test_availability(self) -> None:
        availability = (
            self.client.availability()
        )

        self.assertTrue(
            availability.available
        )
        self.assertEqual(
            availability.version,
            "29.6.2",
        )

    def test_container_inventory(self) -> None:
        containers = (
            self.client.list_containers()
        )

        self.assertEqual(
            len(containers),
            2,
        )
        self.assertEqual(
            containers[0].name,
            "jenkins",
        )
        self.assertEqual(
            containers[0].health,
            "HEALTHY",
        )
        self.assertTrue(
            containers[0].running
        )
        self.assertFalse(
            containers[1].running
        )

    def test_summary(self) -> None:
        summary = self.client.summary()

        self.assertTrue(summary.available)
        self.assertEqual(summary.total, 2)
        self.assertEqual(summary.running, 1)
        self.assertEqual(summary.stopped, 1)
        self.assertEqual(summary.unhealthy, 0)

    def test_server_info(self) -> None:
        information = (
            self.client.server_info()
        )

        self.assertEqual(
            information["architecture"],
            "aarch64",
        )
        self.assertEqual(
            information["containers_running"],
            1,
        )

    def test_inspect(self) -> None:
        inspection = self.client.inspect(
            "jenkins"
        )

        self.assertEqual(
            inspection["name"],
            "jenkins",
        )
        self.assertEqual(
            inspection["image"],
            "jenkins/jenkins:lts",
        )
        self.assertTrue(
            inspection["state"]["Running"]
        )

    def test_stats(self) -> None:
        statistics = self.client.stats(
            ["jenkins"]
        )

        self.assertEqual(
            len(statistics),
            1,
        )
        self.assertEqual(
            statistics[0].name,
            "jenkins",
        )
        self.assertEqual(
            statistics[0].cpu_percent,
            "1.25%",
        )

    def test_logs(self) -> None:
        logs = self.client.logs(
            "jenkins",
            tail=50,
        )

        self.assertIn(
            "fully up and running",
            logs,
        )

    def test_restart(self) -> None:
        restarted = self.client.restart(
            "jenkins"
        )

        self.assertEqual(
            restarted,
            "jenkins",
        )


class FakeApiDockerClient:
    def summary(
        self,
        *,
        include_containers: bool = True,
    ) -> Any:
        class Summary:
            @staticmethod
            def to_dict() -> dict[str, Any]:
                return {
                    "available": True,
                    "version": "29.6.2",
                    "detail": "Docker engine is reachable",
                    "total": 1,
                    "running": 1,
                    "stopped": 0,
                    "unhealthy": 0,
                    "containers": [
                        {
                            "name": "jenkins",
                            "state": "RUNNING",
                        }
                    ],
                }

        return Summary()

    def server_info(self) -> dict[str, Any]:
        return {
            "available": True,
            "version": "29.6.2",
        }

    def stats(
        self,
        containers: list[str] | None = None,
    ) -> list[Any]:
        return []


class DockerApiTests(unittest.TestCase):
    def test_root_and_docker_endpoint(
        self,
    ) -> None:
        from z0.api.server import (
            create_server,
        )

        with patch(
            "z0.api.server.DockerClient",
            FakeApiDockerClient,
        ):
            server = create_server(
                "127.0.0.1",
                0,
            )

            thread = threading.Thread(
                target=server.serve_forever,
                daemon=True,
            )
            thread.start()

            host, port = (
                server.server_address[:2]
            )

            try:
                with urlopen(
                    f"http://{host}:{port}/",
                    timeout=5,
                ) as response:
                    root_payload = json.load(
                        response
                    )

                with urlopen(
                    f"http://{host}:{port}/api/docker",
                    timeout=5,
                ) as response:
                    docker_payload = json.load(
                        response
                    )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

            self.assertEqual(
                root_payload["version"],
                "1.1",
            )
            self.assertIn(
                "/api/docker",
                root_payload["endpoints"],
            )
            self.assertTrue(
                docker_payload["available"]
            )
            self.assertEqual(
                docker_payload["containers"][0]["name"],
                "jenkins",
            )


if __name__ == "__main__":
    unittest.main()
PY

log "Compiling Phase 2 Python modules"

"${PYTHON}" -m compileall -q \
    z0/dockerops \
    z0/docker_cli.py \
    z0/unified_cli.py \
    z0/plugins/builtin/docker.py \
    z0/api/server.py \
    tests/test_dockerops.py

log "Installing updated z0 project"

"${PYTHON}" -m pip install \
    --editable . \
    --no-deps \
    --disable-pip-version-check

hash -r

log "Running Docker operations tests"

"${PYTHON}" -m unittest \
    tests.test_dockerops \
    -v

log "Running existing core tests"

"${PYTHON}" -m unittest discover \
    -s tests \
    -p 'test_core.py' \
    -v

log "Verifying installed CLI commands"

command -v z0 >/dev/null 2>&1 ||
    die "The z0 command was not installed."

command -v z0-docker >/dev/null 2>&1 ||
    die "The z0-docker command was not installed."

echo "z0 command:"
command -v z0

echo "z0-docker command:"
command -v z0-docker

log "Running live Docker engine smoke test"

z0 docker --pretty status

log "Listing Docker containers"

z0 docker ps --all

log "Showing Docker engine information"

z0 docker info

log "Testing Docker API on an ephemeral port"

"${PYTHON}" - <<'PY'
import json
import threading
from urllib.request import urlopen

from z0.api.server import create_server


server = create_server(
    "127.0.0.1",
    0,
)

thread = threading.Thread(
    target=server.serve_forever,
    daemon=True,
)
thread.start()

host, port = server.server_address[:2]

try:
    with urlopen(
        f"http://{host}:{port}/",
        timeout=10,
    ) as response:
        root = json.load(response)

    with urlopen(
        f"http://{host}:{port}/api/docker",
        timeout=20,
    ) as response:
        docker = json.load(response)
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)

assert root["status"] == "ONLINE"
assert root["version"] == "1.1"
assert "/api/docker" in root["endpoints"]
assert docker["available"] is True

print(
    json.dumps(
        {
            "api": "ONLINE",
            "version": root["version"],
            "docker": (
                "ONLINE"
                if docker["available"]
                else "OFFLINE"
            ),
            "containers": docker["total"],
            "running": docker["running"],
            "stopped": docker["stopped"],
        },
        indent=2,
        sort_keys=True,
    )
)
PY

log "Phase 2 Docker operations completed successfully"

echo
echo "Useful commands:"
echo "  z0 docker status"
echo "  z0 docker ps --all"
echo "  z0 docker info"
echo "  z0 docker inspect jenkins"
echo "  z0 docker stats"
echo "  z0 docker stats jenkins"
echo "  z0 docker logs jenkins --tail 50"
echo
echo "Restart requires confirmation:"
echo "  z0 docker restart CONTAINER"
echo
echo "Non-interactive restart:"
echo "  z0 docker restart CONTAINER --yes"
echo
echo "Docker API:"
echo "  curl -s http://127.0.0.1:8081/api/docker | python3 -m json.tool"
echo "  curl -s http://127.0.0.1:8081/api/docker/info | python3 -m json.tool"
echo "  curl -s 'http://127.0.0.1:8081/api/docker/stats' | python3 -m json.tool"
echo "  curl -s 'http://127.0.0.1:8081/api/docker/inspect?container=jenkins' | python3 -m json.tool"
echo
echo "Jenkins was not modified. It remains on port 8080."
echo
echo "Git status:"
git status --short
echo
echo "Diff summary:"
git diff --stat -- \
    pyproject.toml \
    z0/dockerops \
    z0/docker_cli.py \
    z0/unified_cli.py \
    z0/plugins/builtin/docker.py \
    z0/api/server.py \
    tests/test_dockerops.py
echo
echo "Suggested staging command:"
echo "git add \\"
echo "  pyproject.toml \\"
echo "  install-phase2-docker.sh \\"
echo "  z0/dockerops \\"
echo "  z0/docker_cli.py \\"
echo "  z0/unified_cli.py \\"
echo "  z0/plugins/builtin/docker.py \\"
echo "  z0/api/server.py \\"
echo "  tests/test_dockerops.py"
echo
echo "Suggested commit:"
echo 'git commit -m "feat(docker): add Docker monitoring and operations"'
