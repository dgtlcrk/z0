from z0.adapters.base import AdapterStatus
from z0.adapters.discord import DiscordAdapter
from z0.adapters.registry import AdapterRegistry


def test_adapter_status_serializes() -> None:
    status = AdapterStatus(
        name="test",
        enabled=True,
        connected=False,
        state="READY",
    )

    assert status.to_dict()["name"] == "test"


def test_discord_adapter_disabled() -> None:
    adapter = DiscordAdapter(enabled=False)

    assert adapter.status().state == "DISABLED"


def test_registry_rejects_duplicate_names() -> None:
    registry = AdapterRegistry()
    registry.register(DiscordAdapter(enabled=False))

    try:
        registry.register(DiscordAdapter(enabled=False))
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate adapter was accepted")
