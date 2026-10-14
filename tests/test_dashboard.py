"""Dashboard reads saved sources without probing or mutating files."""

import json

import pytest

from z0.network.dashboard import build_monitoring_dashboard


def test_empty_dashboard(tmp_path):
    data = build_monitoring_dashboard(
        inventory_path=tmp_path / "missing-inventory.json",
        availability_path=tmp_path / "missing-availability.json",
    )
    assert data["inventory"]["total"] == 0
    assert data["monitoring"]["total"] == 0
    assert data["events"]["total"] == 0
    assert not list(tmp_path.iterdir())


def test_saved_counts_and_recent_events(tmp_path, monkeypatch):
    inventory = tmp_path / "inventory.json"
    availability = tmp_path / "availability.json"
    inventory.write_text(json.dumps({
        "version": 2,
        "devices": {
            "aa:bb:cc:dd:ee:ff": {
                "mac_address": "aa:bb:cc:dd:ee:ff",
                "ip_address": "192.168.1.5", "hostname": "node",
                "state": "ONLINE", "gateway_status": "on",
                "last_activity": "", "connection_type": "",
                "sources": ["icmp"], "first_seen": "t1",
                "last_observed": "t2", "last_confirmed_online": "t2",
                "observation_count": 2,
            },
        },
    }))
    availability.write_text(json.dumps({
        "version": 1,
        "hosts": {
            "192.168.1.254": {
                "address": "192.168.1.254", "state": "AVAILABLE",
                "successes": 2, "failures": 0, "last_checked": "now",
                "last_success": "now", "last_failure": "",
                "last_transition": "now",
            },
        },
        "events": [
            {"address": "192.168.1.254", "timestamp": "1",
             "old_state": "UNCONFIRMED", "new_state": "UNAVAILABLE",
             "result": "FAILURE"},
            {"address": "192.168.1.254", "timestamp": "2",
             "old_state": "UNAVAILABLE", "new_state": "AVAILABLE",
             "result": "SUCCESS"},
        ],
    }))
    before = (inventory.read_bytes(), availability.read_bytes())

    def no_probe(*args, **kwargs):
        raise AssertionError("Dashboard must not probe")

    monkeypatch.setattr("z0.network.availability.probe_once", no_probe)
    data = build_monitoring_dashboard(
        inventory_path=inventory,
        availability_path=availability,
        recent_limit=1,
    )
    assert data["inventory"]["total"] == 1
    assert data["inventory"]["states"] == {"ONLINE": 1}
    assert data["inventory"]["confirmed_online_history"] == 1
    assert data["monitoring"]["states"] == {"AVAILABLE": 1}
    assert data["events"]["total"] == 2
    assert data["events"]["recent"][0]["timestamp"] == "2"
    assert before == (inventory.read_bytes(), availability.read_bytes())


def test_invalid_event_limit_rejected(tmp_path):
    with pytest.raises(ValueError):
        build_monitoring_dashboard(
            inventory_path=tmp_path / "a",
            availability_path=tmp_path / "b",
            recent_limit=-1,
        )


def test_legacy_eventless_availability_supported(tmp_path):
    path = tmp_path / "availability.json"
    path.write_text('{"version":1,"hosts":{}}')
    data = build_monitoring_dashboard(
        inventory_path=tmp_path / "missing.json",
        availability_path=path,
    )
    assert data["events"]["recent"] == []
