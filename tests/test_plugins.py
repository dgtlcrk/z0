from z0.plugins.registry import build_plugin_registry


def test_builtin_plugins_are_discovered() -> None:
    registry = build_plugin_registry()

    assert "system" in registry.names()
    assert "health" in registry.names()


def test_system_plugin_executes() -> None:
    registry = build_plugin_registry()
    result = registry.execute("system", "status")

    assert "hostname" in result
