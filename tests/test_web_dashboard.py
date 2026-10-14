"""Read-only web monitoring routes on an isolated local test server."""

import json
from http.client import HTTPConnection
from threading import Thread
from unittest.mock import patch

from z0.api.server import create_server


def get(server, path):
    host, port = server.server_address
    connection = HTTPConnection(host, port, timeout=5)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def test_monitor_page_and_saved_json(tmp_path):
    server = create_server("127.0.0.1", 0)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with (
            patch(
                "z0.api.server.build_monitoring_dashboard",
                return_value={
                    "generated_at": "now",
                    "inventory": {
                        "total": 76, "confirmed_online_history": 9,
                        "states": {"ONLINE": 9},
                    },
                    "monitoring": {"total": 1, "states": {}, "hosts": []},
                    "events": {"total": 0, "recent": []},
                },
            ),
            patch("z0.api.server.load_tracked", return_value={}),
        ):
            code, headers, body = get(server, "/monitor")
            assert code == 200
            assert "text/html" in headers["Content-Type"]
            assert b"Network Monitor" in body
            assert b"/api/network/dashboard" in body
            assert "Content-Security-Policy" in headers
            code, headers, body = get(server, "/api/network/dashboard")
            assert code == 200
            assert json.loads(body)["inventory"]["total"] == 76
            code, _, body = get(server, "/api/network/devices")
            assert code == 200
            assert json.loads(body) == []
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_monitor_data_error_returns_503():
    server = create_server("127.0.0.1", 0)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with patch(
            "z0.api.server.build_monitoring_dashboard",
            side_effect=ValueError("invalid snapshot"),
        ):
            status, _, body = get(server, "/api/network/dashboard")
            assert status == 503
            assert b"invalid snapshot" in body
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
