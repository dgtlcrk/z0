"""Network state assessments never invent confirmed offline status."""

from datetime import UTC, datetime, timedelta

import pytest

from z0.network.state_intelligence import assess_states
from z0.network.tracked_inventory import TrackedDevice


NOW = datetime(2026, 10, 14, 12, tzinfo=UTC)


def tracked(state="NOT_OBSERVED", hours_ago=25, confirmed=True):
    observed = (NOW - timedelta(hours=hours_ago)).isoformat()
    return TrackedDevice(
        mac_address="aa:bb:cc:dd:ee:ff",
        ip_address="192.168.1.5",
        hostname="test",
        state=state,
        gateway_status="off",
        last_activity="",
        connection_type="",
        sources=["bgw320"],
        first_seen=observed,
        last_observed=observed,
        last_confirmed_online=observed if confirmed else "",
        observation_count=3,
    )


def assess(record, threshold=24):
    return assess_states({"mac": record}, now=NOW, stale_hours=threshold)[0]


def test_missing_previously_online_is_suspect_not_offline():
    result = assess(tracked())
    assert result.assessment == "SUSPECT"
    assert "negative-probe" in result.reason


def test_missing_recent_device_not_observed():
    assert assess(tracked(hours_ago=1)).assessment == "NOT_OBSERVED"


def test_missing_historical_gateway_only_not_suspect():
    assert assess(tracked(confirmed=False)).assessment == "NOT_OBSERVED"


def test_gateway_on_does_not_claim_online():
    assert assess(tracked(state="GATEWAY_ON")).assessment == "GATEWAY_REPORTED"


def test_online_is_online():
    assert assess(tracked(state="ONLINE")).assessment == "ONLINE"


def test_stale_does_not_mean_offline():
    assert assess(tracked(state="STALE")).assessment == "STALE"


def test_threshold_is_configurable():
    assert assess(tracked(hours_ago=25), threshold=48).assessment == "NOT_OBSERVED"


def test_bad_threshold_rejected():
    with pytest.raises(ValueError, match="greater than zero"):
        assess_states({}, now=NOW, stale_hours=0)


def test_malformed_timestamps_do_not_trigger_suspect():
    record = tracked()
    record.last_observed = "not-a-date"
    assert assess(record).assessment == "NOT_OBSERVED"
