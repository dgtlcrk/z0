"""Friendly labels and browser-inventory regressions."""

import json

import pytest

from z0.api.web_dashboard import PAGE
from z0.network.device_labels import label_devices, load_device_labels


def test_device_labels_from_separate_file(tmp_path):
    path = tmp_path / "labels.json"
    path.write_text(json.dumps({"AA:BB:CC:DD:EE:FF": "Office MacBook"}))
    labels = load_device_labels(path)
    result = label_devices(
        [{"mac_address": "aa:bb:cc:dd:ee:ff", "hostname": "unknown-device"}],
        labels,
    )
    assert result[0]["display_name"] == "Office MacBook"
    assert result[0]["hostname"] == "unknown-device"


def test_label_file_missing_is_safe(tmp_path):
    assert load_device_labels(tmp_path / "missing.json") == {}


def test_invalid_mac_rejected(tmp_path):
    path = tmp_path / "labels.json"
    path.write_text('{"bad-mac":"Test"}')
    with pytest.raises(ValueError, match="MAC"):
        load_device_labels(path)


def test_device_metadata_not_mutated():
    original = [{"mac_address": "", "ip_address": "192.168.1.229",
                 "hostname": "neteng-pi", "state": "ONLINE"}]
    labeled = label_devices(original, {})
    assert labeled[0]["display_name"] == "neteng-pi"
    assert "display_name" not in original[0]


def test_browser_has_controls_and_safe_dom_rendering():
    for control in ('id="search"', 'id="stateFilter"', 'id="sort"'):
        assert control in PAGE
    assert "renderDevices()" in PAGE
    assert "textContent" in PAGE
    assert "innerHTML" not in PAGE
