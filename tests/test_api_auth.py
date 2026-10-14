"""HTTP Basic authentication integration regressions."""

import base64
from http.client import HTTPConnection
from threading import Thread
from unittest.mock import patch

from z0.api.server import create_server


def request(server, path, credentials=None, method="GET"):
    connection = HTTPConnection(*server.server_address, timeout=5)
    try:
        headers = {}
        if credentials is not None:
            token = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
            headers["Authorization"] = "Basic " + token
        connection.request(method, path, headers=headers)
        response = connection.getresponse()
        status = response.status
        response_headers = dict(response.getheaders())
        body = response.read()
        return status, response_headers, body
    finally:
        connection.close()


def test_opt_in_basic_auth_protects_all_routes():
    server = create_server("127.0.0.1", 0)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with patch.dict(
            "os.environ",
            {"Z0_API_AUTH_USERNAME": "admin", "Z0_API_AUTH_PASSWORD": "a-secret"},
        ):
            for path in ("/", "/monitor", "/api/network/dashboard",
                         "/api/network/device?mac=bad", "/api/docker"):
                status, headers, body = request(server, path)
                assert status == 401
                assert "Basic" in headers["WWW-Authenticate"]
                assert b"a-secret" not in body
                assert request(server, path, "admin:wrong")[0] == 401
            assert request(server, "/", "admin:a-secret")[0] == 200
            assert request(server, "/monitor", "admin:a-secret")[0] == 200
            assert request(server, "/", "admin:a-secret", "POST")[0] == 405
            assert request(server, "/", method="POST")[0] == 401
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_partial_config_fails_closed():
    server = create_server("127.0.0.1", 0)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with patch.dict(
            "os.environ",
            {"Z0_API_AUTH_USERNAME": "admin", "Z0_API_AUTH_PASSWORD": ""},
        ):
            status, _, _ = request(server, "/monitor")
            assert status == 503
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_legacy_loopback_defaults_without_credentials():
    server = create_server("127.0.0.1", 0)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with patch.dict(
            "os.environ",
            {"Z0_API_AUTH_USERNAME": "", "Z0_API_AUTH_PASSWORD": ""},
        ):
            assert request(server, "/monitor")[0] == 200
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
