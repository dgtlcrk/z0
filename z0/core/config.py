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
