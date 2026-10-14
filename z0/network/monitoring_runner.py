"""Explicitly opt-in, single-shot availability monitor for systemd timers.

Does not install a timer, change inventory or start a daemon.
Only explicitly configured private IPv4 addresses can be probed.
"""

from __future__ import annotations

import fcntl
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from z0.network.availability import (
    DEFAULT_PATH as AVAILABILITY_PATH,
)
from z0.network.availability import (
    check_targets,
    load_events,
    normalize_targets,
)

DEFAULT_CONFIG = Path.home() / ".config" / "z0" / "monitoring.json"
DEFAULT_LOCK = Path.home() / ".config" / "z0" / "monitoring.lock"


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, object]:
    """Strict configuration; absent config means no checks."""
    if not path.exists():
        return {"enabled": False, "targets": [], "notify": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Monitoring configuration must be a JSON object")
    if set(data) - {"enabled", "targets", "notify"}:
        raise ValueError("Unknown monitoring configuration keys")
    enabled = data.get("enabled", False)
    notify = data.get("notify", False)
    targets = data.get("targets", [])
    if not isinstance(enabled, bool) or not isinstance(notify, bool):
        raise ValueError("Monitoring enabled and notify must be booleans")
    if not isinstance(targets, list) or not all(
        isinstance(address, str) for address in targets
    ):
        raise ValueError("Monitoring targets must be a list of addresses")
    if enabled:
        targets = normalize_targets(targets)
    elif targets:
        # Still reject unsafe targets in disabled configurations.
        targets = normalize_targets(targets)
    return {"enabled": enabled, "notify": notify, "targets": targets}


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    """Prevent two scheduled runs from racing on availability persistence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Monitoring is already running") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run_once(
    *,
    config_path: Path = DEFAULT_CONFIG,
    availability_path: Path = AVAILABILITY_PATH,
    lock_path: Path = DEFAULT_LOCK,
) -> list[str]:
    """Run configured probes once; return optional journal-ready messages."""
    settings = load_config(config_path)
    if not settings["enabled"]:
        return []
    targets = settings["targets"]
    if not isinstance(targets, list):
        raise ValueError("Invalid targets")
    with exclusive_lock(lock_path):
        old_events = load_events(availability_path)
        check_targets(targets, path=availability_path)
        new_events = load_events(availability_path)[len(old_events):]
    if not settings["notify"]:
        return []
    return [
        (
            "z0 monitoring: "
            f"{event.address} {event.old_state} -> {event.new_state} "
            f"at {event.timestamp}"
        )
        for event in new_events
        if event.new_state in {"AVAILABLE", "UNAVAILABLE"}
    ]


def main() -> None:
    try:
        messages = run_once()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"z0 monitoring error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    for message in messages:
        print(message, flush=True)


if __name__ == "__main__":
    main()
