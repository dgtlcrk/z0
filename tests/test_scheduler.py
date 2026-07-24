from pathlib import Path

from z0.scheduler.engine import Scheduler
from z0.scheduler.store import JobStore


def test_scheduler_add_and_remove(tmp_path: Path) -> None:
    scheduler = Scheduler(
        store=JobStore(tmp_path / "jobs.json"),
    )

    job = scheduler.add_job(
        name="System status",
        plugin="system",
        action="status",
        interval_seconds=60,
    )

    assert len(scheduler.list_jobs()) == 1
    assert scheduler.remove_job(job.job_id)
    assert scheduler.list_jobs() == []


def test_scheduler_runs_plugin(tmp_path: Path) -> None:
    scheduler = Scheduler(
        store=JobStore(tmp_path / "jobs.json"),
    )

    job = scheduler.add_job(
        name="System status",
        plugin="system",
        action="status",
        interval_seconds=60,
    )

    result = scheduler.run_job_by_id(job.job_id)

    assert result["last_status"] == "SUCCESS"
    assert "hostname" in result["last_result"]
