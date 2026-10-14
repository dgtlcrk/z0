"""Offline simulation survives reloads and cannot touch live availability."""

import json

import pytest

from z0.network.availability_simulation import load_simulation, simulate


def test_outage_then_recovery_with_durable_history(tmp_path):
    path = tmp_path / "sim.json"
    host, events = simulate("192.168.1.254", "FFFSS", path=path)
    assert host.state == "AVAILABLE"
    assert [(e.old_state, e.new_state) for e in events] == [
        ("UNCONFIRMED", "UNAVAILABLE"),
        ("UNAVAILABLE", "AVAILABLE"),
    ]
    saved_hosts, saved_events = load_simulation(path)
    assert saved_hosts["192.168.1.254"].state == "AVAILABLE"
    assert len(saved_events) == 2
    # Simulate process restart and incremental checks.
    host, new_events = simulate("192.168.1.254", "FFF", path=path)
    assert host.state == "UNAVAILABLE"
    assert len(new_events) == 1
    assert len(load_simulation(path)[1]) == 3


def test_failure_counter_carries_across_calls(tmp_path):
    path = tmp_path / "sim.json"
    simulate("192.168.1.254", "FF", path=path)
    host, events = simulate("192.168.1.254", "F", path=path)
    assert host.state == "UNAVAILABLE"
    assert len(events) == 1


def test_simulation_never_runs_ping(tmp_path, monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Network probe attempted")

    monkeypatch.setattr("z0.network.availability.probe_once", forbid)
    host, _ = simulate("192.168.1.254", "SS", path=tmp_path / "sim.json")
    assert host.state == "AVAILABLE"


def test_reject_invalid_sequence(tmp_path):
    with pytest.raises(ValueError):
        simulate("192.168.1.254", "FAIL", path=tmp_path / "sim.json")


def test_reject_corrupt_history_without_overwrite(tmp_path):
    path = tmp_path / "sim.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        simulate("192.168.1.254", "FFF", path=path)
    assert path.read_text(encoding="utf-8") == "{broken"


def test_production_availability_file_forbidden():
    from z0.network.availability import DEFAULT_PATH

    with pytest.raises(ValueError, match="production"):
        simulate("192.168.1.254", "FFF", path=DEFAULT_PATH)


def test_reject_public_target(tmp_path):
    with pytest.raises(ValueError):
        simulate("8.8.8.8", "FFF", path=tmp_path / "sim.json")
