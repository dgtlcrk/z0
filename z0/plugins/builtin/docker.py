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
