"""Conservative auto-OP join handler tests."""

from types import SimpleNamespace
from unittest.mock import Mock

from z0.services.irc import Z0Bot


class Source:
    nick = "nas-"

    def __init__(self, host):
        self.host = host

    def __str__(self):
        return f"nas-!~lorenzo@{self.host}"


def test_exact_hostmask_receives_op():
    bot = object.__new__(Z0Bot)
    bot.autoop_hostmask = "nas-!~lorenzo@75.40.51.189"
    connection = Mock()
    connection.get_nickname.return_value = "z0_cloud_"
    event = SimpleNamespace(target="#skipland", source=Source("75.40.51.189"))
    bot.on_join(connection, event)
    connection.mode.assert_called_once_with("#skipland", "+o nas-")


def test_same_nick_different_host_rejected():
    bot = object.__new__(Z0Bot)
    bot.autoop_hostmask = "nas-!~lorenzo@75.40.51.189"
    connection = Mock()
    connection.get_nickname.return_value = "z0_cloud_"
    event = SimpleNamespace(target="#skipland", source=Source("203.0.113.10"))
    bot.on_join(connection, event)
    connection.mode.assert_not_called()


def test_autoop_disabled():
    bot = object.__new__(Z0Bot)
    bot.autoop_hostmask = ""
    connection = Mock()
    connection.get_nickname.return_value = "z0_cloud_"
    event = SimpleNamespace(target="#skipland", source=Source("75.40.51.189"))
    bot.on_join(connection, event)
    connection.mode.assert_not_called()
