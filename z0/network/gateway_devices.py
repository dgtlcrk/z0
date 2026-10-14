"""Read-only parsing of AT&T BGW320 LAN-side device records."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path

from z0.network.gateway import DEFAULT_GATEWAY, _fetch

MAC_PATTERN = re.compile(r"^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$", re.I)
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


@dataclass(frozen=True)
class GatewayDevice:
    mac_address: str
    ipv4_address: str
    name: str
    status: str
    last_activity: str
    allocation: str
    connection_type: str
    connection_speed: str
    mesh_client: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class _DeviceTableParser(HTMLParser):
    """Collect TH/TD field pairs from LAN-side device tables only."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_device_table = False
        self.table_depth = 0
        self.cell_kind = ""
        self.cell_parts: list[str] = []
        self.label = ""
        self.current: dict[str, str] = {}
        self.records: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            attrs_map = dict(attrs)
            if self.in_device_table:
                self.table_depth += 1
            elif "LAN-side device" in (attrs_map.get("summary") or ""):
                self.in_device_table = True
                self.table_depth = 1
            return
        if not self.in_device_table:
            return
        if tag in ("th", "td") and not self.cell_kind:
            self.cell_kind = tag
            self.cell_parts = []
        elif tag == "br" and self.cell_kind:
            self.cell_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self.in_device_table and self.cell_kind:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.in_device_table:
            return
        if tag == self.cell_kind:
            value = " ".join("".join(self.cell_parts).split())
            if tag == "th":
                self.label = value
            elif tag == "td" and self.label:
                if self.label == "MAC Address":
                    if self.current:
                        self.records.append(self.current)
                    self.current = {}
                self.current[self.label] = value
                self.label = ""
            self.cell_kind = ""
            self.cell_parts = []
        if tag == "table":
            self.table_depth -= 1
            if self.table_depth == 0:
                if self.current:
                    self.records.append(self.current)
                    self.current = {}
                self.in_device_table = False


def parse_gateway_devices(html: str) -> list[GatewayDevice]:
    parser = _DeviceTableParser()
    parser.feed(html)
    parser.close()
    devices: list[GatewayDevice] = []
    for record in parser.records:
        mac = record.get("MAC Address", "").strip().lower()
        if not MAC_PATTERN.fullmatch(mac):
            continue
        address_name = record.get("IPv4 Address / Name", "")
        ip_match = IP_PATTERN.search(address_name)
        address = ""
        if ip_match:
            try:
                address = str(ipaddress.IPv4Address(ip_match.group()))
            except ipaddress.AddressValueError:
                pass
        name = record.get("Name", "")
        if not name and address_name:
            name = address_name.replace(address, "", 1).strip(" /")
        devices.append(
            GatewayDevice(
                mac_address=mac,
                ipv4_address=address,
                name=name,
                status=record.get("Status", "").strip().lower(),
                last_activity=record.get("Last Activity", ""),
                allocation=record.get("Allocation", ""),
                connection_type=record.get("Connection Type", ""),
                connection_speed=record.get("Connection Speed", ""),
                mesh_client=record.get("Mesh Client", ""),
            )
        )
    return devices


def collect_gateway_devices(
    gateway: str = DEFAULT_GATEWAY, *, html_file: Path | None = None
) -> list[GatewayDevice]:
    """Read a saved HTML page or the BGW320's LAN-side device page.

    Live fetch reuses the existing gateway transport, whose local self-signed
    certificate is currently not verified. Do not expose it outside the LAN.
    """
    html = (
        html_file.read_text(encoding="utf-8")
        if html_file is not None
        else _fetch(gateway, "/cgi-bin/devices.ha", timeout=30)
    )
    return parse_gateway_devices(html)
