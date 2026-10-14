"""IRC transport selection and hostname verification checks."""

from dataclasses import replace
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
    cloud_config = replace(
        service.config,
        use_tls=True,
        server="irc.example.org",
    )
    monkeypatch.setattr(service, "config", cloud_config)

    with (
        patch.object(
            service.irc.bot.SingleServerIRCBot, "__init__", return_value=None
        ) as parent_init,
        patch.object(service.ssl, "create_default_context") as create_context,
    ):
        service.Z0Bot()
        factory = parent_init.call_args.kwargs["connect_factory"]
        sock = object()
        factory.wrapper(sock)
        create_context.return_value.wrap_socket.assert_called_once_with(
            sock, server_hostname="irc.example.org"
        )
