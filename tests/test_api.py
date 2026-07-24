from z0.api.snapshot import build_snapshot


def test_snapshot_contains_platform_sections() -> None:
    snapshot = build_snapshot()

    assert snapshot["platform"]["name"] == "z0_n3t"
    assert "system" in snapshot
    assert "adapters" in snapshot
    assert "plugins" in snapshot
    assert "jobs" in snapshot
