"""Opt-in monitoring runs only configured private targets and emits real events."""

import json

import pytest

from z0.network import availability
from z0.network.monitoring_runner import load_config, run_once


def config(path, **kwargs):
    path.write_text(json.dumps(kwargs), encoding="utf-8")


def test_missing_and_disabled_config_never_probe(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(availability, "probe_once", calls.append)
    assert run_once(
        config_path=tmp_path / "missing.json",
        availability_path=tmp_path / "availability.json",
        lock_path=tmp_path / "lock",
    ) == []
    disabled = tmp_path / "disabled.json"
    config(disabled, enabled=False, targets=["192.168.1.254"], notify=True)
    assert run_once(
        config_path=disabled,
        availability_path=tmp_path / "availability.json",
        lock_path=tmp_path / "lock",
    ) == []
    assert not calls
    assert not (tmp_path / "availability.json").exists()


def test_opt_in_transitions_only_notifies_once(tmp_path, monkeypatch):
    config_path = tmp_path / "monitoring.json"
    available = tmp_path / "availability.json"
    lock = tmp_path / "lock"
    config(config_path, enabled=True, notify=True, targets=["192.168.1.254"])
    outcomes = iter([False, False, False, True, True, True])
    monkeypatch.setattr(availability, "probe_once", lambda _: next(outcomes))
    def go():
        return run_once(
            config_path=config_path, availability_path=available, lock_path=lock
        )
    assert go() == []
    assert go() == []
    errors = go()
    assert len(errors) == 1
    assert "UNCONFIRMED -> UNAVAILABLE" in errors[0]
    assert go() == []
    recovered = go()
    assert len(recovered) == 1
    assert "UNAVAILABLE -> AVAILABLE" in recovered[0]
    assert go() == []
    assert len(availability.load_events(available)) == 2


def test_notify_disabled_still_persists_checks(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    a = tmp_path / "avail.json"
    config(p, enabled=True, notify=False, targets=["192.168.1.254"])
    monkeypatch.setattr(availability, "probe_once", lambda _: False)
    for _ in range(3):
        assert run_once(
            config_path=p, availability_path=a, lock_path=tmp_path / "lock"
        ) == []
    assert availability.load_availability(a)["192.168.1.254"].state == (
        "UNAVAILABLE"
    )


def test_invalid_targets_and_configuration_fail_closed(tmp_path):
    path = tmp_path / "monitoring.json"
    for values in (
        {"enabled": True, "notify": False, "targets": ["8.8.8.8"]},
        {"enabled": "true", "targets": ["192.168.1.8"]},
        {"enabled": True, "targets": []},
        {"enabled": True, "targets": ["192.168.1.8"], "surprise": 1},
    ):
        config(path, **values)
        with pytest.raises(ValueError):
            load_config(path)


def test_lock_prevents_concurrent_runner(tmp_path):
    from z0.network.monitoring_runner import exclusive_lock

    lock = tmp_path / "monitor.lock"
    with exclusive_lock(lock):
        with pytest.raises(RuntimeError, match="already running"):
            with exclusive_lock(lock):
                pass
