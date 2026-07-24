"""Lightweight persistent scheduler engine."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

from z0.plugins.registry import PluginRegistry, build_plugin_registry
from z0.scheduler.models import Job, utc_now
from z0.scheduler.store import JobStore


class Scheduler:
    def __init__(
        self,
        *,
        store: JobStore | None = None,
        plugins: PluginRegistry | None = None,
    ) -> None:
        self.store = store or JobStore()
        self.plugins = plugins or build_plugin_registry()

    def list_jobs(self) -> list[Job]:
        return self.store.load()

    def add_job(
        self,
        *,
        name: str,
        plugin: str,
        action: str,
        interval_seconds: int,
    ) -> Job:
        if interval_seconds < 1:
            raise ValueError("Job interval must be at least one second")

        jobs = self.store.load()

        job = Job(
            name=name,
            plugin=plugin,
            action=action,
            interval_seconds=interval_seconds,
            next_run=utc_now(),
        )

        jobs.append(job)
        self.store.save(jobs)
        return job

    def remove_job(self, job_id: str) -> bool:
        jobs = self.store.load()
        remaining = [job for job in jobs if job.job_id != job_id]

        if len(remaining) == len(jobs):
            return False

        self.store.save(remaining)
        return True

    def run_job(self, job: Job) -> dict[str, Any]:
        job.last_run = utc_now()

        try:
            result = self.plugins.execute(job.plugin, job.action)
            job.last_result = result
            job.last_error = None
            job.last_status = "SUCCESS"
        except Exception as error:
            job.last_result = None
            job.last_error = str(error)
            job.last_status = "FAILED"

        job.next_run = (
            datetime.now(UTC)
            + timedelta(seconds=job.interval_seconds)
        ).isoformat()

        return job.to_dict()

    def run_job_by_id(self, job_id: str) -> dict[str, Any]:
        jobs = self.store.load()

        for job in jobs:
            if job.job_id == job_id:
                result = self.run_job(job)
                self.store.save(jobs)
                return result

        raise KeyError(f"Unknown job: {job_id}")

    def run_due(self) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        jobs = self.store.load()
        results: list[dict[str, Any]] = []

        for job in jobs:
            if not job.enabled:
                continue

            if not job.next_run:
                due = True
            else:
                try:
                    due_time = datetime.fromisoformat(job.next_run)
                    due = due_time <= now
                except ValueError:
                    due = True

            if due:
                results.append(self.run_job(job))

        self.store.save(jobs)
        return results

    def serve_forever(self, poll_seconds: int = 5) -> None:
        if poll_seconds < 1:
            raise ValueError("Poll interval must be at least one second")

        try:
            while True:
                self.run_due()
                time.sleep(poll_seconds)
        except KeyboardInterrupt:
            return
