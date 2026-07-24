from z0.config import Config


def test_config_reads_environment(monkeypatch):
    monkeypatch.setenv("BOT_NAME", "digitalcrack")
    monkeypatch.setenv("IRC_SERVER", "irc.example.net")
    monkeypatch.setenv("IRC_PORT", "6697")
    monkeypatch.setenv("IRC_NICK", "digitalcr")
    monkeypatch.setenv("IRC_CHANNEL", "#automation")

    config = Config.from_env()

    assert config.bot_name == "digitalcrack"
    assert config.server == "irc.example.net"
    assert config.port == 6697
    assert config.nickname == "digitalcr"
    assert config.channel == "#automation"


def test_nickname_defaults_to_bot_name(monkeypatch):
    monkeypatch.setenv("BOT_NAME", "cloud-z0")
    monkeypatch.delenv("IRC_NICK", raising=False)

    config = Config.from_env()

    assert config.nickname == "cloud-z0"


def test_config_supports_platform_mapping_access():
    config = Config.from_env()

    assert config["api"]["host"] == "127.0.0.1"
    assert config["api"]["port"] == 8081
    assert config["irc"]["enabled"] is True
