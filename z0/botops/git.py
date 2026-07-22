"""Git repository collectors used by BotOps."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitInfo:
    repository: str
    branch: str
    commit: str
    status: str


def _run_git(project_root: Path, *arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        )
        return completed.stdout.strip()
    except (
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return None


def collect_git_info(project_root: Path) -> GitInfo:
    branch = _run_git(project_root, "branch", "--show-current")
    commit = _run_git(project_root, "rev-parse", "--short", "HEAD")
    porcelain = _run_git(project_root, "status", "--porcelain")

    if porcelain is None:
        status = "N/A"
    elif porcelain:
        status = "DIRTY"
    else:
        status = "CLEAN"

    return GitInfo(
        repository=project_root.name,
        branch=branch or "N/A",
        commit=commit or "N/A",
        status=status,
    )
