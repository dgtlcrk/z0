"""AT&T BGW gateway status collection."""

from __future__ import annotations

import re
import ssl
import urllib.request
from dataclasses import asdict, dataclass
from html import unescape
from typing import Any

DEFAULT_GATEWAY = "192.168.1.254"


@dataclass(frozen=True)
class GatewayStatus:
    gateway: str
    reachable: bool
    manufacturer: str
    model: str
    software_version: str
    hardware_version: str
    wan_source: str
    wan_status: str
    network_type: str
    public_ipv4: str
    upstream_gateway: str
    primary_dns: str
    secondary_dns: str
    mtu: str
    receive_drops: str
    transmit_drops: str
    receive_errors: str
    transmit_errors: str
    pon_status: str
    uni_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fetch(gateway: str, path: str, *, timeout: float = 5) -> str:
    url = f"https://{gateway}{path}"

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "z0_n3t"},
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=context,
    ) as response:
        return response.read().decode(
            "utf-8",
            errors="replace",
        )


def _clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = unescape(value)
    return " ".join(value.split())


def _table_value(html: str, label: str) -> str:
    pattern = (
        r"<th[^>]*>\s*"
        + re.escape(label)
        + r"\s*</th>\s*"
        r"<td[^>]*>(.*?)</td>"
    )

    match = re.search(
        pattern,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return ""

    return _clean(match.group(1))


def collect_gateway_status(
    gateway: str = DEFAULT_GATEWAY,
) -> GatewayStatus:
    try:
        system_html = _fetch(
            gateway,
            "/cgi-bin/sysinfo.ha",
        )
        broadband_html = _fetch(
            gateway,
            "/cgi-bin/broadbandstatistics.ha",
        )
    except (OSError, TimeoutError):
        return GatewayStatus(
            gateway=gateway,
            reachable=False,
            manufacturer="",
            model="",
            software_version="",
            hardware_version="",
            wan_source="",
            wan_status="",
            network_type="",
            public_ipv4="",
            upstream_gateway="",
            primary_dns="",
            secondary_dns="",
            mtu="",
            receive_drops="",
            transmit_drops="",
            receive_errors="",
            transmit_errors="",
            pon_status="",
            uni_status="",
        )

    return GatewayStatus(
        gateway=gateway,
        reachable=True,
        manufacturer=_table_value(
            system_html,
            "Manufacturer",
        ),
        model=_table_value(
            system_html,
            "Model Number",
        ),
        software_version=_table_value(
            system_html,
            "Software Version",
        ),
        hardware_version=_table_value(
            system_html,
            "Hardware Version",
        ),
        wan_source=_table_value(
            broadband_html,
            "Broadband Connection Source",
        ),
        wan_status=_table_value(
            broadband_html,
            "Broadband Connection",
        ),
        network_type=_table_value(
            broadband_html,
            "Broadband Network Type",
        ),
        public_ipv4=_table_value(
            broadband_html,
            "Broadband IPv4 Address",
        ),
        upstream_gateway=_table_value(
            broadband_html,
            "Gateway IPv4 Address",
        ),
        primary_dns=_table_value(
            broadband_html,
            "Primary DNS",
        ),
        secondary_dns=_table_value(
            broadband_html,
            "Secondary DNS",
        ),
        mtu=_table_value(
            broadband_html,
            "MTU",
        ),
        receive_drops=_table_value(
            broadband_html,
            "Receive Drops",
        ),
        transmit_drops=_table_value(
            broadband_html,
            "Transmit Drops",
        ),
        receive_errors=_table_value(
            broadband_html,
            "Receive Errors",
        ),
        transmit_errors=_table_value(
            broadband_html,
            "Transmit Errors",
        ),
        pon_status=_table_value(
            broadband_html,
            "PON Link Status",
        ),
        uni_status=_table_value(
            broadband_html,
            "UNI Status",
        ),
    )
