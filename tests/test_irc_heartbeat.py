"""Regression tests for IRC heartbeat detection and recovery."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from z0.services.irc import (
    IRC_HEARTBEAT_INTERVAL_SECONDS,
    IRC_HEARTBEAT_TIMEOUT_SECONDS,
    Z0Bot,
)


def make_bot():
    bot = object.__new__(Z0Bot)
    bot._heartbeat_poll_scheduled = False
    bot._heartbeat_pending = None
    bot._heartbeat_deadline = 0.0
    bot._heartbeat_next_due = 0.0
    bot.reactor = SimpleNamespace(scheduler=Mock())
    connection = Mock()
    connection.is_connected.return_value = True
    bot.connection = connection
    return bot, connection


def test_welcome_schedules_one_watchdog_even_after_reconnect():
    bot, connection = make_bot()
    with patch("z0.services.irc.time.monotonic", return_value=100):
        bot.on_welcome(connection, None)
        bot.on_welcome(connection, None)
    bot.reactor.scheduler.execute_every.assert_called_once()
    connection.join.assert_called()


def test_heartbeat_sends_ping_and_accepts_matching_pong():
    bot, connection = make_bot()
    bot._heartbeat_next_due = 60
    with patch("z0.services.irc.time.monotonic", return_value=100):
        bot._check_irc_heartbeat()
        token = bot._heartbeat_pending
        connection.ping.assert_called_once_with(token)
        assert bot._heartbeat_deadline == 100 + IRC_HEARTBEAT_TIMEOUT_SECONDS
        bot.on_pong(connection, SimpleNamespace(arguments=["wrong"]))
        assert bot._heartbeat_pending == token
        bot.on_pong(connection, SimpleNamespace(arguments=[token]))
        assert bot._heartbeat_pending is None
        assert bot._heartbeat_next_due == 100 + IRC_HEARTBEAT_INTERVAL_SECONDS


def test_missing_pong_disconnects_to_trigger_library_reconnect():
    bot, connection = make_bot()
    bot._heartbeat_pending = "z0-test"
    bot._heartbeat_deadline = 130
    with patch("z0.services.irc.time.monotonic", return_value=131):
        bot._check_irc_heartbeat()
    connection.disconnect.assert_called_once_with("IRC heartbeat timeout")
    assert bot._heartbeat_pending is None


def test_disconnected_client_does_not_send_ping():
    bot, connection = make_bot()
    connection.is_connected.return_value = False
    bot._check_irc_heartbeat()
    connection.ping.assert_not_called()


def test_disconnect_clears_pending_heartbeat():
    bot, connection = make_bot()
    bot._heartbeat_pending = "z0-test"
    bot.on_disconnect(connection, None)
    assert bot._heartbeat_pending is None
    assert bot._heartbeat_deadline == 0.0
