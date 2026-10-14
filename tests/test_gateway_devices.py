"""BGW320 device page parsing fixtures based on observed table structures."""

from z0.network.gateway_devices import parse_gateway_devices

SAMPLE = """
<html>
<table class="table100" summary="This table displays info for each LAN-side device">
<tr><th scope="row">MAC Address</th><td class="col2">
06:78:a0:b0:88:df
</td></tr>
<tr><th scope="row">Name</th><td class="col2">
unknown0678a0b088df
</td></tr>
<tr><th scope="row">Last Activity</th><td class="col2">
Thu Aug 27 14:28:29 2026
</td></tr>
<tr><th scope="row">Status</th><td class="col2">off</td></tr>
<tr><th scope="row">Allocation</th><td class="col2">dhcp</td></tr>
<tr><th scope="row">Connection Type</th>
<td class="col2"><pre class="column">Wi-Fi<br />5 GHz Radio-1<br />Type: Home<br />Name: TS1992
</pre></td></tr>
<tr><th scope="row">Mesh Client</th><td class="col2">No</td></tr>
<tr><td colspan="2"><hr /></td></tr>
<tr><th scope="row">MAC Address</th><td class="col2">
36:71:f5:5a:96:96
</td></tr>
<tr><th scope="row">IPv4 Address / Name</th><td class="col2">
192.168.1.245
 / android-dhcp-13
</td></tr>
<tr><th scope="row">Last Activity</th><td class="col2">
Wed Oct 14 01:02:28 2026
</td></tr>
<tr><th scope="row">Status</th><td class="col2">on</td></tr>
</table>
</html>
"""


def test_parse_mac_only_and_ip_name_records():
    devices = parse_gateway_devices(SAMPLE)
    assert len(devices) == 2
    old, active = devices
    assert old.mac_address == "06:78:a0:b0:88:df"
    assert old.ipv4_address == ""
    assert old.name == "unknown0678a0b088df"
    assert old.status == "off"
    assert "Wi-Fi" in old.connection_type
    assert "5 GHz" in old.connection_type
    assert active.mac_address == "36:71:f5:5a:96:96"
    assert active.ipv4_address == "192.168.1.245"
    assert active.name == "android-dhcp-13"
    assert active.status == "on"


def test_ignores_unrelated_tables_and_invalid_mac():
    html = (
        '<table><tr><th>MAC Address</th><td>aa:bb:cc:dd:ee:ff</td>'
        '</tr></table>'
        '<table summary="This table displays info for each LAN-side device">'
        '<tr><th>MAC Address</th><td>not-a-mac</td></tr></table>'
    )
    assert parse_gateway_devices(html) == []


def test_empty_or_changed_page_is_not_a_device():
    assert parse_gateway_devices("<html><body>Login required</body></html>") == []
