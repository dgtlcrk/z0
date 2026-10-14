"""Durable, opt-in delivery of confirmed availability events.

SQLite tracks each (event, channel) independently. Never log credentials.
IRC uses an operator-mounted spool consumed by the existing bot.
"""

from __future__ import annotations

import json
import os
import smtplib
import sqlite3
import ssl
import tempfile
import urllib.request
from email.message import EmailMessage
from pathlib import Path

from z0.network.availability import AvailabilityEvent

DEFAULT_DB = Path.home() / ".config/z0/alert_delivery.sqlite3"
CHANNELS = ("discord", "email", "irc")


def read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    if path.stat().st_mode & 0o077:
        raise ValueError(f"Credential file must be mode 600: {path}")
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise ValueError("Invalid credential configuration line")
        values[key] = value.strip()
    return values


def event_key(event: AvailabilityEvent) -> str:
    return "|".join((
        event.address, event.timestamp, event.old_state, event.new_state,
    ))


def render(event: AvailabilityEvent) -> str:
    state = "DOWN" if event.new_state == "UNAVAILABLE" else "RECOVERED"
    return (
        f"z0_n3t {state}: {event.address} "
        f"({event.old_state} -> {event.new_state}) at {event.timestamp} UTC"
    )


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    os.chmod(path, 0o600)
    db.execute(
        "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS delivery ("
        "event_key TEXT NOT NULL, channel TEXT NOT NULL, "
        "message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', "
        "attempts INTEGER NOT NULL DEFAULT 0, "
        "PRIMARY KEY(event_key, channel))"
    )
    db.commit()
    return db


def enqueue_new_events(
    db: sqlite3.Connection, events: list[AvailabilityEvent]
) -> None:
    """Baseline existing history once, then enqueue durable new transitions."""
    row = db.execute(
        "SELECT value FROM meta WHERE key='event_cursor'"
    ).fetchone()
    if row is None:
        # Avoid flooding historical events when alerting is first installed.
        db.execute(
            "INSERT INTO meta(key,value) VALUES('event_cursor',?)",
            (str(len(events)),),
        )
        db.commit()
        return
    cursor = int(row[0])
    if cursor > len(events):
        raise ValueError("Availability history shrank; alert cursor needs review")
    for event in events[cursor:]:
        if event.new_state not in {"AVAILABLE", "UNAVAILABLE"}:
            continue
        for channel in CHANNELS:
            db.execute(
                "INSERT OR IGNORE INTO delivery(event_key,channel,message) "
                "VALUES(?,?,?)",
                (event_key(event), channel, render(event)),
            )
    db.execute(
        "UPDATE meta SET value=? WHERE key='event_cursor'",
        (str(len(events)),),
    )
    db.commit()


def send_discord(message: str, path: Path) -> None:
    values = read_env(path)
    url = values.get("Z0_DISCORD_WEBHOOK_URL", "")
    if not url.startswith("https://discord.com/api/webhooks/"):
        raise ValueError("Discord webhook not configured")
    request = urllib.request.Request(
        url,
        data=json.dumps({
            "username": "z0_n3t Monitor",
            "content": message,
            "allowed_mentions": {"parse": []},
        }).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "User-Agent": "z0-n3t-monitor/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status not in (200, 204):
            raise OSError("Discord did not accept alert")


def send_email(message: str, path: Path) -> None:
    settings = read_env(path)
    required = (
        "Z0_SMTP_HOST", "Z0_SMTP_PORT", "Z0_SMTP_USERNAME",
        "Z0_SMTP_PASSWORD", "Z0_SMTP_FROM", "Z0_SMTP_TO",
    )
    if any(not settings.get(key) for key in required):
        raise ValueError("SMTP credentials incomplete")
    if (settings["Z0_SMTP_HOST"] != "smtp.gmail.com"
            or settings["Z0_SMTP_PORT"] != "587"):
        raise ValueError("Only Gmail STARTTLS on port 587 is supported")
    msg = EmailMessage()
    msg["From"] = settings["Z0_SMTP_FROM"]
    msg["To"] = settings["Z0_SMTP_TO"]
    msg["Subject"] = "z0_n3t | " + message.split(":", 1)[0]
    msg.set_content(message)
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(
            settings["Z0_SMTP_USERNAME"],
            "".join(settings["Z0_SMTP_PASSWORD"].split()),
        )
        smtp.send_message(msg)


def send_irc(message: str, key: str, spool: Path) -> bool:
    """Queue for existing IRC bot; return True only after receipt exists."""
    import hashlib

    ident = hashlib.sha256(key.encode()).hexdigest()
    pending = spool / "pending" / (ident + ".json")
    receipt = spool / "acks" / (ident + ".ack")
    if receipt.exists():
        receipt.unlink()
        pending.unlink(missing_ok=True)
        return True
    if pending.exists():
        return False
    if not (spool / "pending").is_dir() or not (spool / "acks").is_dir():
        raise ValueError("IRC shared spool not mounted/configured")
    payload = json.dumps({"message": message}) + "\n"
    filename = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=pending.parent, prefix=".z0-", delete=False,
            encoding="utf-8",
        ) as handle:
            filename = handle.name
            os.chmod(filename, 0o640)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(filename, pending)
    finally:
        if filename and os.path.exists(filename):
            os.unlink(filename)
    return False


def deliver_pending(
    db: sqlite3.Connection, *,
    config_dir: Path,
    spool: Path,
) -> dict[str, int]:
    """Attempt channels separately; persist successes, retry failures later."""
    results = {"delivered": 0, "pending": 0}
    rows = db.execute(
        "SELECT event_key,channel,message FROM delivery "
        "WHERE status='pending' ORDER BY rowid"
    ).fetchall()
    for key, channel, message in rows:
        try:
            if channel == "discord":
                send_discord(message, config_dir / "discord.env")
                completed = True
            elif channel == "email":
                send_email(message, config_dir / "smtp.env")
                completed = True
            elif channel == "irc":
                completed = send_irc(message, key, spool)
            else:
                raise ValueError("Unknown alert channel")
        except (OSError, ValueError, KeyError) as exc:
            # Do not print third-party exception text (may contain secrets).
            print(f"z0 alert {channel}: pending ({type(exc).__name__})")
            completed = False
        db.execute(
            "UPDATE delivery SET status=?,attempts=attempts+1 "
            "WHERE event_key=? AND channel=?",
            ("delivered" if completed else "pending", key, channel),
        )
        db.commit()
        results["delivered" if completed else "pending"] += 1
    return results
