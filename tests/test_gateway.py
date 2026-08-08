"""Tests for AT&T BGW gateway collection."""

from z0.network.gateway import (
    GatewayStatus,
    _table_value,
)


def test_gateway_status_to_dict() -> None:
    status = GatewayStatus(
        gateway="192.168.1.254",
        reachable=True,
        manufacturer="HUMAX",
        model="BGW320-500",
        software_version="6.34.7",
        hardware_version="test",
        wan_source="FIBER",
        wan_status="Up",
        network_type="Lightspeed",
        public_ipv4="203.0.113.10",
        upstream_gateway="203.0.113.1",
        primary_dns="192.0.2.10",
        secondary_dns="192.0.2.11",
        mtu="1500",
        receive_drops="0",
        transmit_drops="0",
        receive_errors="0",
        transmit_errors="0",
        pon_status="OPERATION (O5)",
        uni_status="up",
    )

    result = status.to_dict()

    assert result["manufacturer"] == "HUMAX"
    assert result["model"] == "BGW320-500"
    assert result["wan_source"] == "FIBER"
    assert result["pon_status"] == "OPERATION (O5)"


def test_table_value_extracts_gateway_field() -> None:
    html = """
    <tr>
      <th scope="row">Model Number</th>
      <td class="col2">BGW320-500</td>
    </tr>
    """

    assert _table_value(
        html,
        "Model Number",
    ) == "BGW320-500"
