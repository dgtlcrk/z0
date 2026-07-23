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
