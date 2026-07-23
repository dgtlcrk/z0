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
