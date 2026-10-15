"""Conservative auto-OP join handler tests."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from z0.services.irc import Z0Bot


class Source:
    nick = "operator"

    def __init__(self, host):
        self.host = host

    def __str__(self):
        return f"operator!~example@{self.host}"


def test_exact_hostmask_receives_op():
    bot = object.__new__(Z0Bot)
    bot.autoop_hostmask = "operator!~example@198.51.100.10"
    connection = Mock()
    connection.get_nickname.return_value = "z0_test_bot"
    event = SimpleNamespace(target="#example-ops", source=Source("198.51.100.10"))
    with patch("z0.services.irc.config") as config:
        config.channel = "#example-ops"
        bot.on_join(connection, event)
    connection.mode.assert_called_once_with("#example-ops", "+o operator")


def test_same_nick_different_host_rejected():
    bot = object.__new__(Z0Bot)
    bot.autoop_hostmask = "operator!~example@198.51.100.10"
    connection = Mock()
    connection.get_nickname.return_value = "z0_test_bot"
    event = SimpleNamespace(target="#example-ops", source=Source("203.0.113.10"))
    bot.on_join(connection, event)
    connection.mode.assert_not_called()


def test_autoop_disabled():
    bot = object.__new__(Z0Bot)
    bot.autoop_hostmask = ""
    connection = Mock()
    connection.get_nickname.return_value = "z0_test_bot"
    event = SimpleNamespace(target="#example-ops", source=Source("198.51.100.10"))
    bot.on_join(connection, event)
    connection.mode.assert_not_called()
