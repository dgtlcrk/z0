"""Scheduler data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Job:
    name: str
    plugin: str
    action: str
    interval_seconds: int
    enabled: bool = True
    job_id: str = field(default_factory=lambda: uuid4().hex[:12])
    last_run: str | None = None
    next_run: str | None = None
    last_status: str = "NEVER"
    last_result: dict[str, Any] | None = None
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        return cls(**data)
