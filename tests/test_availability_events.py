"""Real manual probe events remain consistent with saved host states."""

import pytest

from z0.network.availability import (
    check_targets,
    load_availability,
    load_events,
)


def test_real_probe_transitions_and_restarts(tmp_path, monkeypatch):
    path = tmp_path / "availability.json"
    responses = iter([False, False, False, True, True])
    monkeypatch.setattr(
        "z0.network.availability.probe_once", lambda address: next(responses)
    )
    for _ in range(5):
        check_targets(["192.168.1.254"], path=path)
    events = load_events(path)
    assert [(e.old_state, e.new_state) for e in events] == [
        ("UNCONFIRMED", "UNAVAILABLE"),
        ("UNAVAILABLE", "AVAILABLE"),
    ]
    assert [e.result for e in events] == ["FAILURE", "SUCCESS"]
    assert load_availability(path)["192.168.1.254"].state == "AVAILABLE"
    assert len(load_events(path)) == 2


def test_preexisting_v1_file_migrates_on_update(tmp_path, monkeypatch):
    path = tmp_path / "availability.json"
    path.write_text(
        '{"version":1,"hosts":{"192.168.1.254":'
        '{"address":"192.168.1.254","state":"AVAILABLE",'
        '"successes":2,"failures":0,"last_checked":"",'
        '"last_success":"","last_failure":"","last_transition":""}}}',
        encoding="utf-8",
    )
    assert load_events(path) == []
    monkeypatch.setattr("z0.network.availability.probe_once", lambda ip: True)
    check_targets(["192.168.1.254"], path=path)
    assert load_events(path) == []
    assert load_availability(path)["192.168.1.254"].state == "AVAILABLE"


def test_failed_probe_call_preserves_file(tmp_path, monkeypatch):
    path = tmp_path / "availability.json"
    monkeypatch.setattr(
        "z0.network.availability.probe_once",
        lambda ip: (_ for _ in ()).throw(OSError("ping missing")),
    )
    with pytest.raises(OSError):
        check_targets(["192.168.1.254"], path=path)
    assert not path.exists()


def test_corrupt_events_fail_closed(tmp_path):
    path = tmp_path / "availability.json"
    path.write_text('{"version":1,"hosts":{},"events":null}')
    with pytest.raises(ValueError, match="events"):
        load_events(path)
