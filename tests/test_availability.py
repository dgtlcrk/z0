"""Availability monitoring safety, transitions, and persistence."""

import json

import pytest

from z0.network.availability import (
    HostAvailability,
    check_targets,
    load_availability,
    normalize_targets,
    save_availability,
    transition,
)


def step(entry, success, index, failures=3, recovery=2):
    return transition(
        entry, success, timestamp=str(index),
        failure_threshold=failures, recovery_threshold=recovery,
    )


def test_three_failures_needed_for_unavailable():
    item = HostAvailability("192.168.1.8")
    for i in range(1, 3):
        item = step(item, False, i)
        assert item.state == "UNCONFIRMED"
    item = step(item, False, 3)
    assert item.state == "UNAVAILABLE"
    assert item.last_transition == "3"


def test_two_successes_for_recovery():
    item = HostAvailability("192.168.1.8")
    for i in range(3):
        item = step(item, False, i)
    item = step(item, True, 4)
    assert item.state == "UNAVAILABLE"
    item = step(item, True, 5)
    assert item.state == "AVAILABLE"


def test_successes_do_not_immediately_confirm_initial_available():
    item = step(HostAvailability("192.168.1.8"), True, 1)
    assert item.state == "UNCONFIRMED"


def test_failures_reset_after_success():
    item = HostAvailability("192.168.1.8")
    item = step(item, False, 1)
    item = step(item, True, 2)
    item = step(item, False, 3)
    assert item.failures == 1


def test_reject_public_loopback_and_link_local():
    for address in ("8.8.8.8", "127.0.0.1", "169.254.1.2"):
        with pytest.raises(ValueError):
            normalize_targets([address])


def test_reject_empty_and_large_batch():
    with pytest.raises(ValueError):
        normalize_targets([])
    with pytest.raises(ValueError):
        normalize_targets([f"192.168.1.{i}" for i in range(1, 18)])


def test_roundtrip(tmp_path):
    path = tmp_path / "availability.json"
    save_availability({"192.168.1.8": HostAvailability("192.168.1.8")}, path)
    assert load_availability(path)["192.168.1.8"].state == "UNCONFIRMED"


def test_corrupt_storage_not_overwritten(tmp_path, monkeypatch):
    path = tmp_path / "availability.json"
    path.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr("z0.network.availability.probe_once", lambda address: True)
    with pytest.raises(json.JSONDecodeError):
        check_targets(["192.168.1.8"], path=path)
    assert path.read_text(encoding="utf-8") == "{broken"


def test_probe_error_does_not_persist(tmp_path, monkeypatch):
    path = tmp_path / "availability.json"

    def explode(address):
        raise OSError("ping is unavailable")

    monkeypatch.setattr("z0.network.availability.probe_once", explode)
    with pytest.raises(OSError):
        check_targets(["192.168.1.8"], path=path)
    assert not path.exists()


def test_explicit_targets_only(tmp_path, monkeypatch):
    calls = []

    def probe(address):
        calls.append(address)
        return True

    monkeypatch.setattr("z0.network.availability.probe_once", probe)
    result = check_targets(
        ["192.168.1.8", "192.168.1.8", "192.168.1.9"],
        path=tmp_path / "availability.json",
    )
    assert calls == ["192.168.1.8", "192.168.1.9"]
    assert len(result) == 2
