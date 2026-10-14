"""IRC transport selection and hostname verification checks."""

from unittest.mock import patch

from z0.config import Config
from z0.services import irc as service


def test_tls_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("IRC_TLS", raising=False)
    assert Config.from_env(platform={}).use_tls is False


def test_tls_flag_enabled(monkeypatch):
    monkeypatch.setenv("IRC_TLS", "true")
    assert Config.from_env(platform={}).use_tls is True


def test_tls_factory_validates_host(monkeypatch):
    # Frozen configuration is replaced at the module boundary.
    from dataclasses import replace

    monkeypatch.setattr(
        service, "config", replace(service.config, use_tls=True, server="irc.example.org")
    )
    with patch.object(service.irc.bot.SingleServerIRCBot, "__init__", return_value=None) as init, patch.object(
        service.ssl, "create_default_context"
    ) as create_context:
        bot = service.Z0Bot()
        factory = init.call_args.kwargs["connect_factory"]
        # Check the socket wrapper uses verified TLS and an explicit hostname.
        sock = object()
        factory.wrapper(sock)
        create_context.return_value.wrap_socket.assert_called_once_with(
            sock, server_hostname="irc.example.org"
        )
