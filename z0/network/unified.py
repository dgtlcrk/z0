"""Read-only unified view of BGW320, ARP and ICMP observations.

Never infer OFFLINE from a missing observation or the gateway's historical
"off" flag. The persistent inventory is intentionally not modified here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from z0.network.devices import NetworkDevice, collect_devices
from z0.network.gateway_devices import GatewayDevice, collect_gateway_devices


@dataclass(frozen=True)
class UnifiedDevice:
    mac_address: str
    ip_address: str
    hostname: str
    state: str
    gateway_status: str
    last_activity: str
    connection_type: str
    sources: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["sources"] = list(self.sources)
        return result


def merge_device_observations(
    gateway_devices: list[GatewayDevice],
    lan_devices: list[NetworkDevice],
) -> list[UnifiedDevice]:
    """Merge independent observations, preferring MAC identity over DHCP IP."""
    by_mac: dict[str, dict[str, str | set[str]]] = {}
    by_ip: dict[str, str] = {}

    for item in gateway_devices:
        mac = item.mac_address.lower()
        if not mac:
            continue
        entry = by_mac.setdefault(
            mac,
            {
                "mac": mac,
                "ip": "",
                "hostname": "",
                "state": "UNKNOWN",
                "gateway_status": "",
                "last_activity": "",
                "connection_type": "",
                "sources": set(),
            },
        )
        entry["sources"].add("bgw320")
        entry["gateway_status"] = item.status
        entry["last_activity"] = item.last_activity
        entry["connection_type"] = item.connection_type
        if item.name:
            entry["hostname"] = item.name
        if item.ipv4_address:
            entry["ip"] = item.ipv4_address
            by_ip[item.ipv4_address] = mac
        if item.status == "on":
            entry["state"] = "GATEWAY_ON"

    for item in lan_devices:
        mac = item.mac_address.lower()
        # Never merge conflicting MAC identities just because DHCP reused an IP.
        if not mac:
            mac = by_ip.get(item.ip_address, "")
            if not mac:
                mac = f"ip:{item.ip_address}"
        entry = by_mac.setdefault(
            mac,
            {
                "mac": "" if mac.startswith("ip:") else mac,
                "ip": "",
                "hostname": "",
                "state": "UNKNOWN",
                "gateway_status": "",
                "last_activity": "",
                "connection_type": "",
                "sources": set(),
            },
        )
        entry["sources"].add("lan")
        if item.ip_address:
            entry["ip"] = item.ip_address
        if item.hostname and (
            not entry["hostname"]
            or str(entry["hostname"]).lower().startswith("unknown")
        ):
            entry["hostname"] = item.hostname
        if item.state == "ONLINE":
            entry["state"] = "ONLINE"
        elif item.state in {"STALE", "DELAY", "PROBE"}:
            if entry["state"] == "UNKNOWN":
                entry["state"] = "STALE"
        if "icmp" in item.source.split("+"):
            entry["sources"].add("icmp")
        if "linux_neighbor" in item.source.split("+"):
            entry["sources"].add("arp")

    return sorted(
        [
            UnifiedDevice(
                mac_address=str(entry["mac"]),
                ip_address=str(entry["ip"]),
                hostname=str(entry["hostname"]),
                state=str(entry["state"]),
                gateway_status=str(entry["gateway_status"]),
                last_activity=str(entry["last_activity"]),
                connection_type=str(entry["connection_type"]),
                sources=tuple(sorted(entry["sources"])),
            )
            for entry in by_mac.values()
        ],
        key=lambda item: (item.ip_address == "", item.ip_address, item.mac_address),
    )


def collect_unified_devices() -> list[UnifiedDevice]:
    """Fetch observations live, without updating the persistent inventory."""
    return merge_device_observations(collect_gateway_devices(), collect_devices())
