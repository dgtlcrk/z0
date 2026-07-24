from z0.platform_cli import build_parser


def test_status_accepts_json_flag() -> None:
    args = build_parser().parse_args(
        ["status", "--json"]
    )

    assert args.command == "status"
    assert args.json is True
