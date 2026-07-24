"""Persistent JSON job storage."""

from __future__ import annotations

import json
from pathlib import Path

from z0.scheduler.models import Job


DEFAULT_JOB_FILE = Path.home() / ".local" / "share" / "z0" / "jobs.json"


class JobStore:
    def __init__(self, path: Path = DEFAULT_JOB_FILE) -> None:
        self.path = path

    def load(self) -> list[Job]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"Unable to load scheduler data: {self.path}"
            ) from error

        return [Job.from_dict(item) for item in data]

    def save(self, jobs: list[Job]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                [job.to_dict() for job in jobs],
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
