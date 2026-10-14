"""Exercise the IRC private-message handler without a network connection."""

import hashlib
import hmac
from types import SimpleNamespace

from z0.services.irc import Z0Bot
from z0.services.op_auth import OpAuthenticator


class FakeConnection:
    def __init__(self):
        self.messages = []
        self.modes = []

    def privmsg(self, target, text):
        self.messages.append((target, text))

    def mode(self, channel, modes):
        self.modes.append((channel, modes))


def send(bot, connection, text):
    # A SimpleNamespace instance's __str__ attribute doesn't override str().
    source = "nas-!exampleuser@trusted"

    class IRCSource:
        nick = "nas-"

        def __str__(self):
            return source

    Z0Bot.on_privmsg(
        bot,
        connection,
        SimpleNamespace(source=IRCSource(), arguments=[text]),
    )


def test_private_challenge_grants_op_only_after_valid_response():
    bot = object.__new__(Z0Bot)
    bot.op_auth = OpAuthenticator("s" * 32, "#skipland")
    connection = FakeConnection()

    send(bot, connection, "op #skipland")
    nonce = connection.messages[-1][1].split(": ", 1)[1].split()[0]
    assert not connection.modes

    send(bot, connection, "op #skipland " + "0" * 64)
    assert not connection.modes

    digest = hmac.new(
        b"s" * 32,
        f"z0-op-v1:#skipland:{nonce}".encode(),
        hashlib.sha256,
    ).hexdigest()
    send(bot, connection, "op #skipland " + digest)
    assert connection.modes == [("#skipland", "+o nas-")]

    send(bot, connection, "op #skipland " + digest)
    assert len(connection.modes) == 1


def test_private_op_disabled_by_default():
    bot = object.__new__(Z0Bot)
    bot.op_auth = None
    connection = FakeConnection()
    send(bot, connection, "op #skipland")
    assert connection.modes == []
    assert connection.messages[-1] == ("nas-", "OP authentication is disabled")
