"""General utilities for the z0 platform."""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .exceptions import CommandExecutionError


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Captured result from an external command."""

    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


def ensure_directory(
    path: str | Path,
    *,
    mode: int | None = None,
) -> Path:
    """Create and return a directory."""

    directory = Path(path).expanduser()
    directory.mkdir(parents=True, exist_ok=True)

    if mode is not None:
        directory.chmod(mode)

    return directory


def atomic_write_text(
    path: str | Path,
    content: str,
    *,
    encoding: str = "utf-8",
    mode: int | None = None,
) -> Path:
    """Atomically replace a text file."""

    destination = Path(path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary_name: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_name = temporary_file.name
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        temporary_path = Path(temporary_name)

        if mode is not None:
            temporary_path.chmod(mode)

        os.replace(temporary_path, destination)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)

    return destination


def run_command(
    command: str | Sequence[str],
    *,
    timeout: float | None = 30,
    check: bool = True,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    shell: bool = False,
) -> CommandResult:
    """Run an external command and capture its output."""

    if isinstance(command, str):
        if shell:
            execution_command: str | list[str] = command
            recorded_command = (command,)
        else:
            execution_command = shlex.split(command)
            recorded_command = tuple(execution_command)
    else:
        execution_command = [str(part) for part in command]
        recorded_command = tuple(execution_command)

    process_environment = None

    if env is not None:
        process_environment = os.environ.copy()
        process_environment.update(env)

    try:
        completed = subprocess.run(
            execution_command,
            cwd=(
                Path(cwd).expanduser()
                if cwd is not None
                else None
            ),
            env=process_environment,
            text=True,
            capture_output=True,
            timeout=timeout,
            shell=shell,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandExecutionError(
            recorded_command,
            124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or f"Timed out after {timeout} seconds",
        ) from exc
    except OSError as exc:
        raise CommandExecutionError(
            recorded_command,
            127,
            stderr=str(exc),
        ) from exc

    result = CommandResult(
        command=recorded_command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )

    if check and not result.succeeded:
        raise CommandExecutionError(
            result.command,
            result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    return result
