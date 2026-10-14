"""Alert durability, independence, default safety, and IRC acknowledgement."""

import json

from z0.network.alert_delivery import (
    connect,
    deliver_pending,
    enqueue_new_events,
    send_irc,
)
from z0.network.availability import AvailabilityEvent


def event(state="UNAVAILABLE"):
    return AvailabilityEvent(
        address="192.168.1.254", timestamp="2026-10-14T11:00:00+00:00",
        old_state="AVAILABLE", new_state=state, result="FAILURE",
    )


def test_initial_history_baseline_does_not_send_old_alerts(tmp_path):
    with connect(tmp_path / "alerts.db") as db:
        enqueue_new_events(db, [event()])
        assert db.execute("SELECT COUNT(*) FROM delivery").fetchone()[0] == 0


def test_enqueue_is_idempotent_per_channel(tmp_path):
    with connect(tmp_path / "alerts.db") as db:
        enqueue_new_events(db, [])
        enqueue_new_events(db, [event()])
        enqueue_new_events(db, [event()])
        rows = db.execute(
            "SELECT channel FROM delivery ORDER BY channel"
        ).fetchall()
        assert [row[0] for row in rows] == ["discord", "email", "irc"]


def test_channel_failures_do_not_block_delivery(tmp_path, monkeypatch):
    import z0.network.alert_delivery as alerts

    with connect(tmp_path / "alerts.db") as db:
        enqueue_new_events(db, [])
        enqueue_new_events(db, [event()])
        calls = []
        def email(message, path):
            calls.append("email")
            raise OSError("unavailable")
        def discord(message, path):
            calls.append("discord")
        def irc(message, key, spool):
            calls.append("irc")
            return False
        monkeypatch.setattr(alerts, "send_email", email)
        monkeypatch.setattr(alerts, "send_discord", discord)
        monkeypatch.setattr(alerts, "send_irc", irc)
        result = deliver_pending(
            db, config_dir=tmp_path, spool=tmp_path / "spool"
        )
        assert result == {"delivered": 1, "pending": 2}
        assert sorted(calls) == ["discord", "email", "irc"]
        assert db.execute(
            "SELECT status FROM delivery WHERE channel='discord'"
        ).fetchone()[0] == "delivered"
        calls.clear()
        deliver_pending(db, config_dir=tmp_path, spool=tmp_path / "spool")
        assert "discord" not in calls


def test_irc_spool_waits_for_acknowledgement(tmp_path):
    key = "address|time|AVAILABLE|UNAVAILABLE"
    (tmp_path / "pending").mkdir()
    (tmp_path / "acks").mkdir()
    assert not send_irc("z0_n3t DOWN: 192.168.1.254", key, tmp_path)
    files = list((tmp_path / "pending").glob("*.json"))
    assert len(files) == 1
    assert files[0].stat().st_mode & 0o777 == 0o640
    assert json.loads(files[0].read_text())["message"].startswith("z0_n3t")
    assert not send_irc("z0_n3t DOWN: 192.168.1.254", key, tmp_path)
    (tmp_path / "acks" / (files[0].stem + ".ack")).touch()
    assert send_irc("z0_n3t DOWN: 192.168.1.254", key, tmp_path)
    assert list((tmp_path / "pending").iterdir()) == []


def test_unknown_channel_not_marked_delivered(tmp_path):
    with connect(tmp_path / "alerts.db") as db:
        db.execute(
            "INSERT INTO delivery(event_key,channel,message) VALUES(?,?,?)",
            ("id", "other", "test"),
        )
        db.commit()
        result = deliver_pending(
            db, config_dir=tmp_path, spool=tmp_path / "spool"
        )
        assert result == {"delivered": 0, "pending": 1}


def test_database_is_private(tmp_path):
    with connect(tmp_path / "alerts.db"):
        pass
    assert (tmp_path / "alerts.db").stat().st_mode & 0o777 == 0o600
