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
