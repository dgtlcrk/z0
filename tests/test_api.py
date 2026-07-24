from z0.api.snapshot import build_snapshot


def test_snapshot_contains_platform_sections() -> None:
    snapshot = build_snapshot()

    assert snapshot["platform"]["name"] == "z0_n3t"
    assert "system" in snapshot
    assert "adapters" in snapshot
    assert "plugins" in snapshot
    assert "jobs" in snapshot


def test_api_server_uses_package_version() -> None:
    from z0 import __version__
    from z0.api.server import Z0RequestHandler

    assert Z0RequestHandler.server_version == (
        f"z0_n3t/{__version__}"
    )
