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
