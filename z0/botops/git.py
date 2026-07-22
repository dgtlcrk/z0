"""Git repository collectors used by BotOps."""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GitInfo:
    repository: str
    branch: str
    commit: str
    status: str
    remote: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
    remote = _run_git(project_root, "remote", "get-url", "origin")

    if porcelain is None:
        status = "N/A"
    elif porcelain:
        status = "DIRTY"
    else:
        status = "CLEAN"

    return GitInfo(
        repository=project_root.name,
        branch=branch or "DETACHED",
        commit=commit or "N/A",
        status=status,
        remote=remote or "N/A",
    )
