"""Read-only single-device detail API tests."""

import json
from http.client import HTTPConnection
from threading import Thread
from unittest.mock import patch

from z0.api.server import create_server
from z0.api.web_dashboard import PAGE
from z0.network.availability import AvailabilityEvent, HostAvailability
from z0.network.device_details import get_device_details
from z0.network.tracked_inventory import TrackedDevice


def record():
    return TrackedDevice(
        mac_address="48:e2:ad:86:ff:61",
        ip_address="192.168.1.254",
        hostname="BGW320-500",
        state="ONLINE",
        gateway_status="ON",
        last_activity="", connection_type="Ethernet",
        sources=["gateway", "icmp"],
        first_seen="2026-10-01T00:00:00+00:00",
        last_observed="2026-10-14T00:00:00+00:00",
        last_confirmed_online="2026-10-14T00:00:00+00:00",
        observation_count=3,
    )


def test_saved_details_correlate_real_events_without_probes():
    with (
        patch("z0.network.device_details.load_tracked",
              return_value={"gateway": record()}),
        patch("z0.network.device_details.load_device_labels",
              return_value={"48:e2:ad:86:ff:61": "Home gateway"}),
        patch("z0.network.device_details.load_availability",
              return_value={"192.168.1.254":
                            HostAvailability(address="192.168.1.254",
                                             state="AVAILABLE")}),
        patch("z0.network.device_details.load_events",
              return_value=[AvailabilityEvent(
                  address="192.168.1.254", timestamp="now",
                  old_state="UNCONFIRMED", new_state="AVAILABLE",
                  result="SUCCESS")]),
        patch("z0.network.availability.probe_once",
              side_effect=AssertionError("unexpected probe")),
    ):
        result = get_device_details("48:e2:ad:86:ff:61")
        assert result is not None
        assert result["device"]["display_name"] == "Home gateway"
        assert result["device"]["hostname"] == "BGW320-500"
        assert result["availability"]["state"] == "AVAILABLE"
        assert result["event_count"] == 1
        assert get_device_details("missing") is None


def test_detail_http_statuses_and_page():
    server = create_server("127.0.0.1", 0)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with patch("z0.api.server.get_device_details",
                   return_value={"device": {"hostname": "gateway"}}):
            for path, expected in [
                ("/api/network/device", 400),
                ("/api/network/device?mac=missing", 200),
            ]:
                conn = HTTPConnection(*server.server_address, timeout=5)
                try:
                    conn.request("GET", path)
                    response = conn.getresponse()
                    assert response.status == expected
                    if expected == 200:
                        assert json.loads(response.read())["device"]
                    else:
                        response.read()
                finally:
                    conn.close()
        with patch("z0.api.server.get_device_details", return_value=None):
            conn = HTTPConnection(*server.server_address, timeout=5)
            try:
                conn.request("GET", "/api/network/device?mac=missing")
                response = conn.getresponse()
                assert response.status == 404
                response.read()
            finally:
                conn.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    assert 'id="details"' in PAGE
    assert "openDetails(device)" in PAGE
    assert "textContent" in PAGE
    assert "innerHTML" not in PAGE
