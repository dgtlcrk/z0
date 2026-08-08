from z0.platform_cli import build_parser


def test_status_accepts_json_flag() -> None:
    args = build_parser().parse_args(
        ["status", "--json"]
    )

    assert args.command == "status"
    assert args.json is True


def test_adapters_accepts_json_flag() -> None:
    args = build_parser().parse_args(
        ["adapters", "--json"]
    )

    assert args.command == "adapters"
    assert args.json is True


def test_adapters_human_output(capsys) -> None:
    from z0.platform_cli import _print_adapters

    _print_adapters(
        [
            {
                "name": "irc",
                "state": "REACHABLE",
                "enabled": True,
                "connected": False,
                "detail": "irc.prison.net:6697",
            }
        ]
    )

    output = capsys.readouterr().out

    assert "Adapters" in output
    assert "irc" in output
    assert "REACHABLE" in output
    assert "irc.prison.net:6697" in output


def test_plugins_accepts_json_flag() -> None:
    args = build_parser().parse_args(
        ["plugins", "--json"]
    )

    assert args.command == "plugins"
    assert args.json is True


def test_plugins_human_output(capsys) -> None:
    from z0.platform_cli import _print_plugins

    _print_plugins(
        [
            {
                "name": "health",
                "version": "1.0.0",
                "enabled": True,
                "description": (
                    "Check configured infrastructure targets"
                ),
            }
        ]
    )

    output = capsys.readouterr().out

    assert "Plugins" in output
    assert "health" in output
    assert "1.0.0" in output
    assert "YES" in output
    assert "Check configured infrastructure targets" in output


def test_jobs_list_accepts_json_flag() -> None:
    args = build_parser().parse_args(
        ["jobs", "list", "--json"]
    )

    assert args.command == "jobs"
    assert args.jobs_command == "list"
    assert args.json is True


def test_jobs_human_output(capsys) -> None:
    from z0.platform_cli import _print_jobs

    _print_jobs(
        [
            {
                "job_id": "5b8b86cc9fd8",
                "name": "Infrastructure health",
                "plugin": "health",
                "action": "check",
                "enabled": True,
                "interval_seconds": 300,
                "last_status": "SUCCESS",
                "last_run": "2026-07-24T18:37:33+00:00",
                "next_run": "2026-07-24T18:42:33+00:00",
                "last_error": None,
            }
        ]
    )

    output = capsys.readouterr().out

    assert "Scheduler Jobs" in output
    assert "Infrastructure health" in output
    assert "5b8b86cc9fd8" in output
    assert "5m" in output
    assert "SUCCESS" in output


def test_job_time_with_microseconds_keeps_utc() -> None:
    from z0.platform_cli import _format_job_time

    result = _format_job_time(
        "2026-07-24T19:02:36.123456+00:00"
    )

    assert result == "2026-07-24 19:02:36 UTC"


def test_unified_version_command(capsys) -> None:
    from z0 import __version__
    from z0.unified_cli import main

    result = main(["version"])
    output = capsys.readouterr().out

    assert result == 0
    assert output.strip() == f"z0_n3t {__version__}"


def test_network_status_accepts_json_flag() -> None:
    args = build_parser().parse_args(
        ["network", "status", "--json"]
    )

    assert args.command == "network"
    assert args.network_command == "status"
    assert args.json is True


def test_network_gateway_accepts_json_flag() -> None:
    args = build_parser().parse_args(
        ["network", "gateway", "--json"]
    )

    assert args.command == "network"
    assert args.network_command == "gateway"
    assert args.json is True


def test_network_neighbors_accepts_json_flag() -> None:
    args = build_parser().parse_args(
        ["network", "neighbors", "--json"]
    )

    assert args.command == "network"
    assert args.network_command == "neighbors"
    assert args.json is True


def test_network_devices_accepts_json_flag() -> None:
    args = build_parser().parse_args(
        ["network", "devices", "--json"]
    )

    assert args.command == "network"
    assert args.network_command == "devices"
    assert args.json is True


def test_network_discover_accepts_json_flag() -> None:
    args = build_parser().parse_args(
        ["network", "discover", "--json"]
    )

    assert args.command == "network"
    assert args.network_command == "discover"
    assert args.json is True
