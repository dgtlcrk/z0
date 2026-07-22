from types import SimpleNamespace

from z0.commands import core


def test_ping_returns_pong():
    assert core.ping() == "PONG"


def test_help_lists_primary_commands():
    response = core.help_text()

    assert "!help" in response
    assert "!about" in response
    assert "!dns <host>" in response
    assert "!trace <host>" in response


def test_uptime_formats_elapsed_time(monkeypatch):
    monkeypatch.setattr(core, "START_TIME", 0.0)
    monkeypatch.setattr(core.time, "monotonic", lambda: 3661.0)

    assert core.uptime() == "Uptime: 1h 1m 1s"


def test_about_uses_runtime_identity(monkeypatch):
    monkeypatch.setattr(
        core,
        "config",
        SimpleNamespace(bot_name="digitalcrack"),
    )

    response = core.about()

    assert response.startswith("digitalcrack • Python ")
    assert response.endswith("• Network Automation Platform")
