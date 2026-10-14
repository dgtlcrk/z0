"""Assemble a single device detail using saved records only."""

from __future__ import annotations

from z0.network.availability import load_availability, load_events
from z0.network.device_labels import label_devices, load_device_labels
from z0.network.tracked_inventory import load_tracked


def get_device_details(identifier: str) -> dict[str, object] | None:
    """Resolve exact MAC or IP; no network calls, scans or writes."""
    records = load_tracked()
    matching = [
        record for record in records.values()
        if identifier.lower() == record.mac_address.lower()
        or identifier == record.ip_address
    ]
    if not matching:
        return None
    if len(matching) != 1:
        raise ValueError("Ambiguous device identifier")
    device = label_devices([matching[0].to_dict()], load_device_labels())[0]
    address = matching[0].ip_address
    availability = load_availability().get(address) if address else None
    events = [
        item.to_dict() for item in load_events()
        if address and item.address == address
    ]
    events.sort(key=lambda item: item["timestamp"], reverse=True)
    return {
        "device": device,
        "availability": availability.to_dict() if availability else None,
        "events": events,
        "event_count": len(events),
    }
