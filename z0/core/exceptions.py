"""Shared exceptions for the z0 platform."""

from __future__ import annotations

from collections.abc import Sequence


class Z0Error(Exception):
    """Base exception for expected z0 failures."""


class ConfigurationError(Z0Error):
    """Raised when configuration is missing or invalid."""


class ValidationError(Z0Error, ValueError):
    """Raised when input validation fails."""


class SerializationError(Z0Error):
    """Raised when data cannot be serialized or loaded."""


class ServiceError(Z0Error):
    """Raised when a service operation fails."""


class CommandExecutionError(Z0Error):
    """Raised when an external command fails."""

    def __init__(
        self,
        command: str | Sequence[str],
        returncode: int,
        *,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        if isinstance(command, str):
            command_text = command
        else:
            command_text = " ".join(str(part) for part in command)

        self.command = command_text
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

        detail = stderr.strip() or stdout.strip()
        message = (
            f"Command failed with exit code {returncode}: {command_text}"
        )

        if detail:
            message = f"{message}: {detail}"

        super().__init__(message)
