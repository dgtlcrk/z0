"""Validation helpers shared by z0 modules."""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path

from .exceptions import ValidationError


HOST_LABEL_PATTERN = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$"
)


def validate_port(value: int | str) -> int:
    """Validate a TCP or UDP port."""

    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"Port must be an integer; received {value!r}"
        ) from exc

    if not 1 <= port <= 65535:
        raise ValidationError(
            f"Port must be between 1 and 65535; received {port}"
        )

    return port


def validate_positive_int(
    value: int | str,
    *,
    name: str = "value",
    allow_zero: bool = False,
) -> int:
    """Validate a positive integer."""

    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"{name} must be an integer; received {value!r}"
        ) from exc

    minimum = 0 if allow_zero else 1

    if number < minimum:
        description = "zero or greater" if allow_zero else "greater than zero"
        raise ValidationError(
            f"{name} must be {description}; received {number}"
        )

    return number


def validate_interval(value: int | str) -> int:
    """Validate a scheduler interval in seconds."""

    interval = validate_positive_int(
        value,
        name="interval_seconds",
    )

    if interval > 31_536_000:
        raise ValidationError(
            "interval_seconds cannot exceed one year"
        )

    return interval


def validate_hostname(value: str) -> str:
    """Validate and normalize a hostname or IP address."""

    hostname = value.strip()

    if not hostname:
        raise ValidationError("Hostname cannot be empty")

    try:
        return str(ipaddress.ip_address(hostname))
    except ValueError:
        pass

    hostname = hostname.rstrip(".")

    if len(hostname) > 253:
        raise ValidationError("Hostname exceeds 253 characters")

    labels = hostname.split(".")

    if any(
        not HOST_LABEL_PATTERN.fullmatch(label)
        for label in labels
    ):
        raise ValidationError(f"Invalid hostname: {value!r}")

    return hostname.lower()


def validate_domain(value: str) -> str:
    """Validate and normalize a DNS domain."""

    domain = validate_hostname(value)

    try:
        ipaddress.ip_address(domain)
    except ValueError:
        pass
    else:
        raise ValidationError(
            f"Expected a domain, not an IP address: {value!r}"
        )

    if "." not in domain:
        raise ValidationError(
            f"Domain must contain at least one dot: {value!r}"
        )

    return domain


def validate_existing_path(
    value: str | Path,
    *,
    directory: bool | None = None,
) -> Path:
    """Validate an existing filesystem path."""

    path = Path(value).expanduser()

    if not path.exists():
        raise ValidationError(f"Path does not exist: {path}")

    if directory is True and not path.is_dir():
        raise ValidationError(f"Expected a directory: {path}")

    if directory is False and not path.is_file():
        raise ValidationError(f"Expected a file: {path}")

    return path
