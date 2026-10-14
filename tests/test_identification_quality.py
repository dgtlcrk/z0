"""Identification labels derive from saved data without identity guesses."""

from z0.api.web_dashboard import PAGE
from z0.network.device_labels import identification, label_devices


def test_operator_label_is_distinct_from_observed_hostname():
    device = {
        "mac_address": "ea:5b:ca:3d:17:c2",
        "ip_address": "",
        "hostname": "Lorenzos-MacBook-Air",
        "state": "UNKNOWN",
    }
    result = label_devices([device], {"ea:5b:ca:3d:17:c2": "Work laptop"})
    assert result[0]["display_name"] == "Work laptop"
    assert result[0]["identification_source"] == "operator_label"
    assert result[0]["hostname"] == "Lorenzos-MacBook-Air"
    assert result[0]["locally_administered_mac"] is True
    assert "display_name" not in device


def test_observed_hostname_is_not_a_user_label():
    result = identification(
        {"mac_address": "48:e2:ad:86:ff:61", "hostname": "BGW320-500"},
        {},
    )
    assert result["display_name"] == "BGW320-500"
    assert result["identification_source"] == "observed_hostname"
    assert result["locally_administered_mac"] is False


def test_collector_unknown_name_is_not_device_identification():
    result = identification(
        {"mac_address": "06:78:a0:b0:88:df",
         "hostname": "unknown0678a0b088df"}, {},
    )
    assert result["display_name"] == "Unidentified (06:78:a0:b0:88:df)"
    assert result["identification_source"] == "unidentified"


def test_unidentified_no_mac_uses_saved_ip():
    result = identification(
        {"mac_address": "", "ip_address": "192.168.1.22", "hostname": ""}, {},
    )
    assert result["display_name"] == "Unidentified (192.168.1.22)"
    assert result["locally_administered_mac"] is False


def test_browser_displays_provenance_and_unknown_filter():
    assert 'id="unidentifiedOnly"' in PAGE
    assert "identification_source==='unidentified'" in PAGE
    assert "'Identity source'" in PAGE
    assert "locally_administered_mac" in PAGE
    assert "innerHTML" not in PAGE
