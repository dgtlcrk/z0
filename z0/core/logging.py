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
