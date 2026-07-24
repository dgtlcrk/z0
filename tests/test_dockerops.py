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
