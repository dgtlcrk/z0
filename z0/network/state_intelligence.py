"""Conservative read-only device state assessment over inventory v2.

Inventory v2 stores timestamps and latest observations, but not repeated
negative probes. Thus this module NEVER claims confirmed OFFLINE.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from z0.network.tracked_inventory import TrackedDevice


@dataclass(frozen=True)
class StateAssessment:
    identity: str
    ip_address: str
    hostname: str
    observed_state: str
    assessment: str
    reason: str
    last_observed: str
    last_confirmed_online: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        return None
    return timestamp.astimezone(UTC)


def assess_states(
    inventory: dict[str, TrackedDevice],
    *,
    now: datetime | None = None,
    stale_hours: float = 24,
) -> list[StateAssessment]:
    """Assess observations, never inferring OFFLINE from absence alone."""
    if stale_hours <= 0:
        raise ValueError("stale_hours must be greater than zero")
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        raise ValueError("now must be timezone aware")
    reference = reference.astimezone(UTC)
    results: list[StateAssessment] = []
    for key, record in sorted(inventory.items()):
        last_observed = _parse_time(record.last_observed)
        confirmed = _parse_time(record.last_confirmed_online)
        age_hours = (
            max(0.0, (reference - last_observed).total_seconds() / 3600)
            if last_observed is not None
            else None
        )
        if record.state == "ONLINE":
            assessment, reason = "ONLINE", "Latest scan confirmed reachability"
        elif record.state == "GATEWAY_ON":
            assessment, reason = (
                "GATEWAY_REPORTED",
                "Gateway reports connected; reachability unconfirmed",
            )
        elif record.state == "NOT_OBSERVED":
            if confirmed and age_hours is not None and age_hours >= stale_hours:
                assessment, reason = (
                    "SUSPECT",
                    "Previously reachable device absent beyond threshold; "
                    "no negative-probe evidence",
                )
            else:
                assessment, reason = (
                    "NOT_OBSERVED",
                    "Absent from last collection; not confirmed offline",
                )
        elif record.state == "STALE":
            assessment, reason = "STALE", "Neighbor observation not confirmed online"
        else:
            assessment, reason = "UNKNOWN", "Insufficient reachability evidence"
        results.append(
            StateAssessment(
                identity=key,
                ip_address=record.ip_address,
                hostname=record.hostname,
                observed_state=record.state,
                assessment=assessment,
                reason=reason,
                last_observed=record.last_observed,
                last_confirmed_online=record.last_confirmed_online,
            )
        )
    return results
