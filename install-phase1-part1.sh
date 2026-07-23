#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

error_handler() {
    local exit_code=$?
    local line_number="${1:-unknown}"
    echo
    echo "ERROR: ${SCRIPT_NAME} failed at line ${line_number}."
    echo "Exit code: ${exit_code}"
    exit "${exit_code}"
}

trap 'error_handler $LINENO' ERR

log() {
    echo
    echo "[$(date -u +%H:%M:%S)] $*"
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

if [[ "$(id -u)" -eq 0 ]]; then
    die "Do not run this installer with sudo."
fi

command -v git >/dev/null 2>&1 || die "Git is required."

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" ||
    die "Run this from inside the z0 Git repository."

cd "${REPO_ROOT}"

[[ -d z0 ]] || die "The z0 package directory was not found."
[[ -f pyproject.toml ]] || die "pyproject.toml was not found."
[[ -x .venv/bin/python ]] || die "The .venv virtual environment was not found."

PYTHON="${REPO_ROOT}/.venv/bin/python"
BACKUP_DIR="${REPO_ROOT}/.z0-backups/phase1-part1/${TIMESTAMP}"

log "Repository: ${REPO_ROOT}"
log "Python: ${PYTHON}"

"${PYTHON}" - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit(
        f"Python 3.10 or newer is required. Found {sys.version.split()[0]}"
    )

print(f"Python {sys.version.split()[0]} verified")
PY

TARGET_FILES=(
    "z0/core/__init__.py"
    "z0/core/exceptions.py"
    "z0/core/paths.py"
    "z0/core/config.py"
    "z0/core/logging.py"
    "z0/core/serialization.py"
    "z0/core/time.py"
    "z0/core/validation.py"
    "z0/core/utils.py"
    "tests/test_core.py"
)

BACKUP_CREATED=0

for relative_path in "${TARGET_FILES[@]}"; do
    if [[ -e "${REPO_ROOT}/${relative_path}" ]]; then
        mkdir -p "${BACKUP_DIR}/$(dirname "${relative_path}")"
        cp -a \
            "${REPO_ROOT}/${relative_path}" \
            "${BACKUP_DIR}/${relative_path}"
        BACKUP_CREATED=1
    fi
done

if [[ "${BACKUP_CREATED}" -eq 1 ]]; then
    log "Existing files backed up to ${BACKUP_DIR}"
fi

mkdir -p z0/core tests

log "Creating shared exception classes"

cat > z0/core/exceptions.py <<'PY'
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
PY

log "Creating platform path management"

cat > z0/core/paths.py <<'PY'
"""Filesystem paths used by the z0 platform."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _path_from_environment(name: str, fallback: Path) -> Path:
    value = os.environ.get(name)

    if value:
        return Path(value).expanduser()

    return fallback.expanduser()


def _home_directory() -> Path:
    configured_home = os.environ.get("HOME")

    if configured_home:
        return Path(configured_home).expanduser()

    return Path.home()


@dataclass(frozen=True, slots=True)
class PlatformPaths:
    """Resolved z0 configuration and runtime directories."""

    config_dir: Path
    data_dir: Path
    state_dir: Path
    cache_dir: Path
    log_dir: Path
    history_dir: Path

    @classmethod
    def resolve(cls) -> "PlatformPaths":
        """Resolve paths using Z0 and XDG environment variables."""

        home = _home_directory()

        xdg_config = _path_from_environment(
            "XDG_CONFIG_HOME",
            home / ".config",
        )
        xdg_data = _path_from_environment(
            "XDG_DATA_HOME",
            home / ".local" / "share",
        )
        xdg_state = _path_from_environment(
            "XDG_STATE_HOME",
            home / ".local" / "state",
        )
        xdg_cache = _path_from_environment(
            "XDG_CACHE_HOME",
            home / ".cache",
        )

        config_dir = _path_from_environment(
            "Z0_CONFIG_DIR",
            xdg_config / "z0",
        )
        data_dir = _path_from_environment(
            "Z0_DATA_DIR",
            xdg_data / "z0",
        )
        state_dir = _path_from_environment(
            "Z0_STATE_DIR",
            xdg_state / "z0",
        )
        cache_dir = _path_from_environment(
            "Z0_CACHE_DIR",
            xdg_cache / "z0",
        )
        log_dir = _path_from_environment(
            "Z0_LOG_DIR",
            state_dir / "logs",
        )
        history_dir = _path_from_environment(
            "Z0_HISTORY_DIR",
            data_dir / "history",
        )

        return cls(
            config_dir=config_dir,
            data_dir=data_dir,
            state_dir=state_dir,
            cache_dir=cache_dir,
            log_dir=log_dir,
            history_dir=history_dir,
        )

    @property
    def botops_env_file(self) -> Path:
        return self.config_dir / "botops.env"

    @property
    def scheduler_store(self) -> Path:
        return self.data_dir / "scheduler" / "jobs.json"

    def ensure(self) -> "PlatformPaths":
        """Create all required directories."""

        for directory in (
            self.config_dir,
            self.data_dir,
            self.state_dir,
            self.cache_dir,
            self.log_dir,
            self.history_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        return self
PY

log "Creating validation helpers"

cat > z0/core/validation.py <<'PY'
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
PY

log "Creating configuration helpers"

cat > z0/core/config.py <<'PY'
"""Environment-based configuration for z0."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from .exceptions import ConfigurationError
from .paths import PlatformPaths
from .validation import validate_port


T = TypeVar("T")

TRUE_VALUES = frozenset(
    {"1", "true", "yes", "on", "enabled"}
)
FALSE_VALUES = frozenset(
    {"0", "false", "no", "off", "disabled"}
)


def parse_bool(value: str | bool | int) -> bool:
    """Convert an environment-style value to Boolean."""

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()

    if normalized in TRUE_VALUES:
        return True

    if normalized in FALSE_VALUES:
        return False

    raise ConfigurationError(
        f"Invalid Boolean value {value!r}"
    )


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1]:
        if value[0] in {"'", '"'}:
            return value[1:-1]

    return value


def load_env_file(
    path: str | Path,
    *,
    apply: bool = True,
    override: bool = False,
) -> dict[str, str]:
    """Load a basic KEY=VALUE environment file."""

    env_path = Path(path).expanduser()

    if not env_path.exists():
        return {}

    try:
        lines = env_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except OSError as exc:
        raise ConfigurationError(
            f"Unable to read {env_path}: {exc}"
        ) from exc

    values: dict[str, str] = {}

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            raise ConfigurationError(
                f"{env_path}:{line_number}: expected KEY=VALUE"
            )

        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = _strip_quotes(raw_value.strip())

        if not key:
            raise ConfigurationError(
                f"{env_path}:{line_number}: empty variable name"
            )

        if not key.replace("_", "").isalnum() or key[0].isdigit():
            raise ConfigurationError(
                f"{env_path}:{line_number}: invalid variable {key!r}"
            )

        values[key] = value

        if apply and (override or key not in os.environ):
            os.environ[key] = value

    return values


def _cast_value(
    name: str,
    value: Any,
    cast: Callable[[Any], T] | type[T],
) -> T:
    if cast is bool:
        return parse_bool(value)  # type: ignore[return-value]

    try:
        return cast(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(
            f"Unable to convert {name}={value!r}"
        ) from exc


def env(
    name: str,
    default: T | None = None,
    *,
    cast: Callable[[Any], T] | type[T] = str,
    required: bool = False,
    environ: Mapping[str, str] | None = None,
) -> T:
    """Read and convert an environment variable."""

    source = os.environ if environ is None else environ
    raw_value = source.get(name)

    if raw_value is None or raw_value == "":
        if required:
            raise ConfigurationError(
                f"Required environment variable {name} is not set"
            )

        if default is None:
            return default  # type: ignore[return-value]

        if isinstance(default, str) and cast is not str:
            return _cast_value(name, default, cast)

        return default

    return _cast_value(name, raw_value, cast)


@dataclass(frozen=True, slots=True)
class PlatformSettings:
    """Settings shared by the z0 services and CLI."""

    platform_name: str
    node_name: str
    api_host: str
    api_port: int
    log_level: str
    debug: bool
    paths: PlatformPaths

    @classmethod
    def from_environment(
        cls,
        env_file: str | Path | None = None,
    ) -> "PlatformSettings":
        """Load settings from the environment."""

        paths = PlatformPaths.resolve()

        if env_file is not None:
            selected_env_file = Path(env_file).expanduser()
        else:
            configured_file = os.environ.get("Z0_ENV_FILE")
            selected_env_file = (
                Path(configured_file).expanduser()
                if configured_file
                else paths.botops_env_file
            )

        if selected_env_file.exists():
            load_env_file(selected_env_file)

        paths = PlatformPaths.resolve()

        return cls(
            platform_name=env(
                "Z0_PLATFORM_NAME",
                "z0_n3t",
                cast=str,
            ),
            node_name=env(
                "Z0_NODE_NAME",
                os.uname().nodename,
                cast=str,
            ),
            api_host=env(
                "Z0_API_HOST",
                "127.0.0.1",
                cast=str,
            ),
            api_port=validate_port(
                env("Z0_API_PORT", 8081, cast=int)
            ),
            log_level=env(
                "Z0_LOG_LEVEL",
                "INFO",
                cast=str,
            ).upper(),
            debug=env(
                "Z0_DEBUG",
                False,
                cast=bool,
            ),
            paths=paths,
        )

    def ensure_directories(self) -> "PlatformSettings":
        self.paths.ensure()
        return self
PY

log "Creating command and filesystem utilities"

cat > z0/core/utils.py <<'PY'
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
PY

log "Creating JSON serialization helpers"

cat > z0/core/serialization.py <<'PY'
"""JSON serialization helpers for z0."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .exceptions import SerializationError
from .utils import atomic_write_text


def to_jsonable(value: Any) -> Any:
    """Convert common Python objects to JSON-compatible values."""

    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Enum):
        return to_jsonable(value.value)

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, Mapping):
        return {
            str(key): to_jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, set):
        return sorted(
            (to_jsonable(item) for item in value),
            key=str,
        )

    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [to_jsonable(item) for item in value]

    if hasattr(value, "to_dict") and callable(value.to_dict):
        return to_jsonable(value.to_dict())

    if hasattr(value, "__dict__"):
        return to_jsonable(
            {
                key: item
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        )

    return str(value)


def dumps(
    value: Any,
    *,
    pretty: bool = False,
    sort_keys: bool = True,
) -> str:
    """Serialize a value to JSON."""

    try:
        return json.dumps(
            to_jsonable(value),
            indent=2 if pretty else None,
            sort_keys=sort_keys,
            ensure_ascii=False,
            separators=None if pretty else (",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise SerializationError(
            f"Unable to serialize value: {exc}"
        ) from exc


def loads(content: str) -> Any:
    """Deserialize JSON text."""

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise SerializationError(
            f"Invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc


def dump_file(
    path: str | Path,
    value: Any,
    *,
    pretty: bool = True,
    mode: int | None = None,
) -> Path:
    """Atomically write a JSON file."""

    content = dumps(value, pretty=pretty)

    if not content.endswith("\n"):
        content += "\n"

    try:
        return atomic_write_text(
            path,
            content,
            mode=mode,
        )
    except OSError as exc:
        raise SerializationError(
            f"Unable to write JSON file {path}: {exc}"
        ) from exc


def load_file(
    path: str | Path,
    *,
    default: Any = None,
) -> Any:
    """Load a JSON file."""

    file_path = Path(path).expanduser()

    if not file_path.exists():
        return default

    try:
        return loads(
            file_path.read_text(encoding="utf-8")
        )
    except OSError as exc:
        raise SerializationError(
            f"Unable to read JSON file {file_path}: {exc}"
        ) from exc
PY

log "Creating UTC time helpers"

cat > z0/core/time.py <<'PY'
"""UTC time and duration helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(tz=UTC)


def isoformat_utc(value: datetime | None = None) -> str:
    """Return a normalized UTC ISO-8601 timestamp."""

    selected = utc_now() if value is None else value

    if selected.tzinfo is None:
        selected = selected.replace(tzinfo=UTC)
    else:
        selected = selected.astimezone(UTC)

    return selected.isoformat()


def parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and normalize it to UTC."""

    normalized = value.strip()

    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"

    parsed = datetime.fromisoformat(normalized)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def total_seconds(
    value: timedelta | int | float,
) -> int:
    """Return a non-negative whole-second duration."""

    if isinstance(value, timedelta):
        seconds = int(value.total_seconds())
    else:
        seconds = int(value)

    return max(0, seconds)


def human_duration(
    value: timedelta | int | float,
) -> str:
    """Format a compact human-readable duration."""

    seconds = total_seconds(value)

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)

    parts: list[str] = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    if remaining_seconds or not parts:
        parts.append(f"{remaining_seconds}s")

    return " ".join(parts)
PY

log "Creating logging helpers"

cat > z0/core/logging.py <<'PY'
"""Logging configuration for z0."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


STANDARD_FIELDS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class UTCFormatter(logging.Formatter):
    """Text formatter that emits UTC timestamps."""

    converter = staticmethod(
        lambda timestamp: datetime.fromtimestamp(
            timestamp,
            tz=UTC,
        ).timetuple()
    )


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=UTC,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(
                record.exc_info
            )

        for key, value in record.__dict__.items():
            if (
                key not in STANDARD_FIELDS
                and not key.startswith("_")
            ):
                payload[key] = value

        return json.dumps(
            payload,
            default=str,
            ensure_ascii=False,
            sort_keys=True,
        )


def _normalize_level(
    level: str | int | None,
) -> int:
    if level is None:
        level = os.environ.get("Z0_LOG_LEVEL", "INFO")

    if isinstance(level, int):
        return level

    numeric_level = logging.getLevelName(level.upper())

    if not isinstance(numeric_level, int):
        raise ValueError(f"Unknown logging level: {level!r}")

    return numeric_level


def configure_logging(
    name: str = "z0",
    *,
    level: str | int | None = None,
    log_file: str | Path | None = None,
    json_output: bool = False,
    force: bool = False,
) -> logging.Logger:
    """Configure and return a z0 logger."""

    logger = logging.getLogger(name)
    logger.setLevel(_normalize_level(level))
    logger.propagate = False

    if logger.handlers and not force:
        return logger

    if force:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    if json_output:
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = UTCFormatter(
            fmt="%(asctime)sZ %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file is not None:
        file_path = Path(log_file).expanduser()
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a logger inside the z0 namespace."""

    if name == "z0" or name.startswith("z0."):
        return logging.getLogger(name)

    return logging.getLogger(f"z0.{name}")
PY

log "Creating core package exports"

cat > z0/core/__init__.py <<'PY'
"""Shared foundation for the z0 operations platform."""

from .config import (
    PlatformSettings,
    env,
    load_env_file,
    parse_bool,
)
from .exceptions import (
    CommandExecutionError,
    ConfigurationError,
    SerializationError,
    ServiceError,
    ValidationError,
    Z0Error,
)
from .logging import configure_logging, get_logger
from .paths import PlatformPaths
from .serialization import (
    dump_file,
    dumps,
    load_file,
    loads,
    to_jsonable,
)
from .time import (
    human_duration,
    isoformat_utc,
    parse_datetime,
    total_seconds,
    utc_now,
)
from .utils import (
    CommandResult,
    atomic_write_text,
    ensure_directory,
    run_command,
)
from .validation import (
    validate_domain,
    validate_existing_path,
    validate_hostname,
    validate_interval,
    validate_port,
    validate_positive_int,
)

__all__ = [
    "CommandExecutionError",
    "CommandResult",
    "ConfigurationError",
    "PlatformPaths",
    "PlatformSettings",
    "SerializationError",
    "ServiceError",
    "ValidationError",
    "Z0Error",
    "atomic_write_text",
    "configure_logging",
    "dump_file",
    "dumps",
    "ensure_directory",
    "env",
    "get_logger",
    "human_duration",
    "isoformat_utc",
    "load_env_file",
    "load_file",
    "loads",
    "parse_bool",
    "parse_datetime",
    "run_command",
    "to_jsonable",
    "total_seconds",
    "utc_now",
    "validate_domain",
    "validate_existing_path",
    "validate_hostname",
    "validate_interval",
    "validate_port",
    "validate_positive_int",
]
PY

log "Creating focused unit tests"

cat > tests/test_core.py <<'PY'
"""Tests for the z0 shared core."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from z0.core import (
    ConfigurationError,
    PlatformPaths,
    PlatformSettings,
    ValidationError,
    atomic_write_text,
    dump_file,
    env,
    human_duration,
    isoformat_utc,
    load_env_file,
    load_file,
    parse_bool,
    parse_datetime,
    run_command,
    to_jsonable,
    validate_domain,
    validate_hostname,
    validate_interval,
    validate_port,
)


class BooleanTests(unittest.TestCase):
    def test_boolean_values(self) -> None:
        self.assertTrue(parse_bool("yes"))
        self.assertTrue(parse_bool("ENABLED"))
        self.assertFalse(parse_bool("no"))
        self.assertFalse(parse_bool("disabled"))

    def test_invalid_boolean(self) -> None:
        with self.assertRaises(ConfigurationError):
            parse_bool("maybe")


class EnvironmentTests(unittest.TestCase):
    def test_env_casting(self) -> None:
        source = {
            "TEST_PORT": "8081",
            "TEST_ENABLED": "true",
        }

        self.assertEqual(
            env("TEST_PORT", cast=int, environ=source),
            8081,
        )
        self.assertTrue(
            env("TEST_ENABLED", cast=bool, environ=source)
        )

    def test_load_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "test.env"
            path.write_text(
                "TEST_ALPHA=one\n"
                'TEST_BETA="two words"\n',
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                values = load_env_file(path)

                self.assertEqual(values["TEST_ALPHA"], "one")
                self.assertEqual(
                    os.environ["TEST_BETA"],
                    "two words",
                )


class PathTests(unittest.TestCase):
    def test_xdg_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            environment = {
                "HOME": str(root),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_DATA_HOME": str(root / "data"),
                "XDG_STATE_HOME": str(root / "state"),
                "XDG_CACHE_HOME": str(root / "cache"),
            }

            with patch.dict(os.environ, environment, clear=True):
                paths = PlatformPaths.resolve().ensure()

                self.assertEqual(
                    paths.config_dir,
                    root / "config" / "z0",
                )
                self.assertEqual(
                    paths.history_dir,
                    root / "data" / "z0" / "history",
                )
                self.assertTrue(paths.log_dir.is_dir())


class SettingsTests(unittest.TestCase):
    def test_default_api_port(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            environment = {
                "HOME": str(root),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_DATA_HOME": str(root / "data"),
                "XDG_STATE_HOME": str(root / "state"),
                "XDG_CACHE_HOME": str(root / "cache"),
            }

            with patch.dict(os.environ, environment, clear=True):
                settings = PlatformSettings.from_environment()

                self.assertEqual(settings.api_port, 8081)
                self.assertEqual(
                    settings.api_host,
                    "127.0.0.1",
                )


class SerializationTests(unittest.TestCase):
    def test_to_jsonable(self) -> None:
        @dataclass
        class Example:
            path: Path
            created_at: datetime
            names: set[str]

        value = Example(
            path=Path("/tmp/example"),
            created_at=datetime(
                2026,
                7,
                23,
                8,
                0,
                tzinfo=UTC,
            ),
            names={"beta", "alpha"},
        )

        converted = to_jsonable(value)

        self.assertEqual(converted["path"], "/tmp/example")
        self.assertEqual(
            converted["names"],
            ["alpha", "beta"],
        )

    def test_json_file_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "data.json"
            payload = {"status": "ONLINE", "count": 3}

            dump_file(path, payload)

            self.assertEqual(load_file(path), payload)


class UtilityTests(unittest.TestCase):
    def test_atomic_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "file.txt"

            atomic_write_text(path, "first")
            atomic_write_text(path, "second")

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "second",
            )

    def test_run_command(self) -> None:
        result = run_command(
            [
                sys.executable,
                "-c",
                "print('core-ok')",
            ]
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(result.stdout.strip(), "core-ok")


class TimeTests(unittest.TestCase):
    def test_time_round_trip(self) -> None:
        original = datetime(
            2026,
            7,
            23,
            8,
            0,
            tzinfo=UTC,
        )

        parsed = parse_datetime(
            isoformat_utc(original)
        )

        self.assertEqual(parsed, original)

    def test_human_duration(self) -> None:
        self.assertEqual(
            human_duration(90061),
            "1d 1h 1m 1s",
        )


class ValidationTests(unittest.TestCase):
    def test_port(self) -> None:
        self.assertEqual(validate_port("8081"), 8081)

        with self.assertRaises(ValidationError):
            validate_port(70000)

    def test_interval(self) -> None:
        self.assertEqual(validate_interval(300), 300)

        with self.assertRaises(ValidationError):
            validate_interval(0)

    def test_hostname(self) -> None:
        self.assertEqual(
            validate_hostname("NetEng-Pi.local"),
            "neteng-pi.local",
        )
        self.assertEqual(
            validate_hostname("192.168.1.173"),
            "192.168.1.173",
        )

    def test_domain(self) -> None:
        self.assertEqual(
            validate_domain("TS1992.NET"),
            "ts1992.net",
        )

        with self.assertRaises(ValidationError):
            validate_domain("192.168.1.173")


if __name__ == "__main__":
    unittest.main()
PY

log "Compiling the new Python modules"

"${PYTHON}" -m compileall -q \
    z0/core \
    tests/test_core.py

log "Installing the updated project"

"${PYTHON}" -m pip install \
    --editable . \
    --no-deps \
    --disable-pip-version-check

log "Running focused unit tests"

"${PYTHON}" -m unittest discover \
    -s tests \
    -p 'test_core.py' \
    -v

log "Running core smoke test"

"${PYTHON}" - <<'PY'
from z0.core import (
    PlatformSettings,
    dumps,
    human_duration,
    run_command,
    validate_domain,
)

settings = PlatformSettings.from_environment()
settings.ensure_directories()

branch = run_command(
    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
    timeout=10,
).stdout.strip()

result = {
    "core": "ONLINE",
    "platform": settings.platform_name,
    "node": settings.node_name,
    "api_host": settings.api_host,
    "api_port": settings.api_port,
    "branch": branch,
    "domain": validate_domain("ts1992.net"),
    "duration_test": human_duration(3661),
}

print(dumps(result, pretty=True))
PY

log "Phase 1 Part 1 completed successfully"

echo
echo "Git status:"
git status --short

echo
echo "Suggested commit:"
echo 'git add z0/core tests/test_core.py install-phase1-part1.sh'
echo 'git commit -m "feat(core): add shared platform foundation"'
