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
