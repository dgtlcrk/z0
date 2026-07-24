"""Git repository collectors used by BotOps."""

from __future__ import annotations

import subprocess
import sys
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


def _resolve_git_root(project_root: Path) -> Path:
    candidates = (
        project_root,
        Path.cwd(),
        Path(sys.prefix).parent,
    )

    for candidate in candidates:
        root = _run_git(
            candidate,
            "rev-parse",
            "--show-toplevel",
        )

        if root:
            return Path(root)

    return project_root


def collect_git_info(project_root: Path) -> GitInfo:
    git_root = _resolve_git_root(project_root)

    branch = _run_git(
        git_root,
        "branch",
        "--show-current",
    )
    commit = _run_git(
        git_root,
        "rev-parse",
        "--short",
        "HEAD",
    )
    porcelain = _run_git(
        git_root,
        "status",
        "--porcelain",
    )
    remote = _run_git(
        git_root,
        "remote",
        "get-url",
        "origin",
    )

    if porcelain is None:
        status = "N/A"
    elif porcelain:
        status = "DIRTY"
    else:
        status = "CLEAN"

    repository = git_root.name

    if repository in {
        "site-packages",
        "dist-packages",
    }:
        repository = "z0"

    return GitInfo(
        repository=repository,
        branch=branch or "DETACHED",
        commit=commit or "N/A",
        status=status,
        remote=remote or "N/A",
    )
