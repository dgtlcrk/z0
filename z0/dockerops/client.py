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
