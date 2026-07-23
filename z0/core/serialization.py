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
