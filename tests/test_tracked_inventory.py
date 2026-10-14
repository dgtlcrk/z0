"""Versioned inventory regression tests without touching the user's data."""

import json

import pytest

from z0.network.tracked_inventory import (
    load_tracked,
    merge_tracked,
    save_tracked,
)
from z0.network.unified import UnifiedDevice


def device(mac="aa:bb:cc:dd:ee:ff", state="ONLINE", sources=("icmp",)):
    return UnifiedDevice(
        mac_address=mac,
        ip_address="192.168.1.50",
        hostname="test",
        state=state,
        gateway_status="off",
        last_activity="",
        connection_type="Wi-Fi",
        sources=sources,
    )


def test_roundtrip_and_last_confirmed_online(tmp_path):
    path = tmp_path / "unified.json"
    first = merge_tracked({}, [device()], timestamp="2026-10-14T00:00:00+00:00")
    save_tracked(first, path)
    loaded = load_tracked(path)
    key = "aa:bb:cc:dd:ee:ff"
    assert loaded[key].last_confirmed_online == "2026-10-14T00:00:00+00:00"
    second = merge_tracked(
        loaded, [device(state="GATEWAY_ON", sources=("bgw320",))],
        timestamp="2026-10-14T01:00:00+00:00",
    )
    assert second[key].last_confirmed_online == loaded[key].last_confirmed_online
    assert second[key].observation_count == 2
    assert second[key].first_seen == loaded[key].first_seen
    assert second[key].state == "GATEWAY_ON"


def test_missed_scan_does_not_mark_offline():
    first = merge_tracked({}, [device()], timestamp="first")
    second = merge_tracked(first, [], timestamp="second")
    record = second["aa:bb:cc:dd:ee:ff"]
    assert record.state == "NOT_OBSERVED"
    assert record.last_observed == "first"
    assert record.last_confirmed_online == "first"
    assert first["aa:bb:cc:dd:ee:ff"].state == "ONLINE"


def test_corrupt_file_is_not_silently_discarded(tmp_path):
    path = tmp_path / "unified.json"
    path.write_text("{invalid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_tracked(path)
    assert path.read_text(encoding="utf-8") == "{invalid"


def test_unknown_schema_rejected(tmp_path):
    path = tmp_path / "unified.json"
    path.write_text('{"version": 3, "devices": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        load_tracked(path)


def test_duplicate_identity_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        merge_tracked({}, [device(), device()])


def test_randomized_macs_not_conflated():
    first = merge_tracked({}, [device("aa:bb:cc:dd:ee:01")])
    second = merge_tracked(first, [device("aa:bb:cc:dd:ee:02")])
    assert len(second) == 2
