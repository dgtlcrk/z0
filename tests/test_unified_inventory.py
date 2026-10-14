"""Unified observation merging must preserve identities and uncertainty."""

from z0.network.devices import NetworkDevice
from z0.network.gateway_devices import GatewayDevice
from z0.network.unified import merge_device_observations


def gateway(mac, ip="", status="off", name="device"):
    return GatewayDevice(mac, ip, name, status, "", "dhcp", "Wi-Fi", "", "No")


def lan(mac, ip, state="ONLINE", source="icmp+linux_neighbor"):
    return NetworkDevice(ip, mac, "", "wlan0", state, source, "neighbor")


def test_gateway_records_preserved_without_ipv4_or_ping():
    result = merge_device_observations(
        [gateway("aa:bb:cc:dd:ee:01")], []
    )
    assert len(result) == 1
    assert result[0].state == "UNKNOWN"
    assert result[0].gateway_status == "off"
    assert result[0].ip_address == ""


def test_arp_and_ping_enrich_existing_gateway_identity():
    result = merge_device_observations(
        [gateway("aa:bb:cc:dd:ee:01", status="off")],
        [lan("aa:bb:cc:dd:ee:01", "192.168.1.20")],
    )
    assert len(result) == 1
    assert result[0].state == "ONLINE"
    assert result[0].gateway_status == "off"
    assert {"bgw320", "lan", "arp", "icmp"} == set(result[0].sources)


def test_gateway_on_distinct_from_confirmed_reachable():
    result = merge_device_observations(
        [gateway("aa:bb:cc:dd:ee:01", status="on")], []
    )
    assert result[0].state == "GATEWAY_ON"


def test_stale_lan_observation_is_not_offline():
    result = merge_device_observations(
        [], [lan("aa:bb:cc:dd:ee:01", "192.168.1.20", "STALE", "linux_neighbor")]
    )
    assert result[0].state == "STALE"


def test_different_macs_with_reused_ip_remain_distinct():
    result = merge_device_observations(
        [gateway("aa:bb:cc:dd:ee:01", "192.168.1.20")],
        [lan("aa:bb:cc:dd:ee:02", "192.168.1.20")],
    )
    assert len(result) == 2


def test_unknown_mac_can_match_gateway_ip():
    result = merge_device_observations(
        [gateway("aa:bb:cc:dd:ee:01", "192.168.1.20")],
        [lan("", "192.168.1.20")],
    )
    assert len(result) == 1
