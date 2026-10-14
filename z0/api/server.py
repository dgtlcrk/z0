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

from z0 import __version__
from z0.api.web_dashboard import PAGE
from z0.config import config
from z0.core import (
    PlatformSettings,
    to_jsonable,
)
from z0.dockerops import (
    DockerClient,
    docker_error_payload,
)
from z0.network.dashboard import build_monitoring_dashboard
from z0.network.device_details import get_device_details
from z0.network.device_labels import label_devices, load_device_labels
from z0.network.tracked_inventory import load_tracked

LOGGER = logging.getLogger("z0.api")

API_ENDPOINTS = [
    "/monitor",
    "/api/network/dashboard",
    "/api/network/devices",
    "/api/network/device?mac=MAC",
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

    server_version = f"z0_n3t/{__version__}"
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

    def _send_html(self, page: str) -> None:
        encoded = page.encode("utf-8")
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", (
            "default-src 'none'; style-src 'unsafe-inline'; "
            "script-src 'unsafe-inline'; connect-src 'self'"
        ))
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
                    "version": __version__,
                    "endpoints": API_ENDPOINTS,
                }
            )
            return

        if path == "/monitor":
            self._send_html(PAGE)
            return

        if path == "/api/network/device":
            identifier = self._first_query_value(query, "mac").strip()
            if not identifier or len(identifier) > 64:
                self._send_error_payload(
                    HTTPStatus.BAD_REQUEST, "A valid mac parameter is required"
                )
                return
            try:
                details = get_device_details(identifier)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                self._send_error_payload(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    f"Saved device details unavailable: {exc}",
                )
                return
            if details is None:
                self._send_error_payload(
                    HTTPStatus.NOT_FOUND, "Device not found in saved inventory"
                )
                return
            self._send_json(details)
            return

        if path in {"/api/network/dashboard", "/api/network/devices"}:
            try:
                if path == "/api/network/dashboard":
                    payload = build_monitoring_dashboard()
                else:
                    payload = label_devices(
                        [
                            record.to_dict()
                            for _, record in sorted(load_tracked().items())
                        ],
                        load_device_labels(),
                    )
            except (OSError, ValueError, TypeError, KeyError) as exc:
                self._send_error_payload(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    f"Saved monitoring data unavailable: {exc}",
                )
                return
            self._send_json(payload)
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
    host: str = config["api"]["host"],
    port: int = config["api"]["port"],
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
