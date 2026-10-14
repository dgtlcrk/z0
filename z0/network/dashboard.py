"""Read-only monitoring dashboard assembled from saved on-disk snapshots."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from z0.network.availability import DEFAULT_PATH as AVAILABILITY_PATH
from z0.network.availability import load_availability, load_events
from z0.network.tracked_inventory import DEFAULT_PATH as INVENTORY_PATH
from z0.network.tracked_inventory import load_tracked


def build_monitoring_dashboard(
    *,
    inventory_path: Path = INVENTORY_PATH,
    availability_path: Path = AVAILABILITY_PATH,
    recent_limit: int = 10,
) -> dict[str, object]:
    """Read snapshots only; never launch a probe or modify local data."""
    if recent_limit < 0 or recent_limit > 100:
        raise ValueError("recent_limit must be between 0 and 100")
    inventory = load_tracked(inventory_path)
    hosts = load_availability(availability_path)
    events = load_events(availability_path)
    state_counts = Counter(item.state for item in inventory.values())
    availability_counts = Counter(item.state for item in hosts.values())
    recent = sorted(events, key=lambda event: event.timestamp, reverse=True)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "inventory": {
            "total": len(inventory),
            "states": dict(sorted(state_counts.items())),
            "confirmed_online_history": sum(
                bool(item.last_confirmed_online) for item in inventory.values()
            ),
        },
        "monitoring": {
            "total": len(hosts),
            "states": dict(sorted(availability_counts.items())),
            "hosts": [
                item.to_dict() for _, item in sorted(hosts.items())
            ],
        },
        "events": {
            "total": len(events),
            "recent": [event.to_dict() for event in recent[:recent_limit]],
        },
    }
