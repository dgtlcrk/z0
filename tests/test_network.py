from z0.commands import network


def test_valid_network_targets():
    assert network._valid_target("example.com")
    assert network._valid_target("subdomain.example.com")
    assert network._valid_target("8.8.8.8")
    assert network._valid_target("2001:4860:4860::8888")


def test_rejects_unsafe_network_targets():
    assert not network._valid_target("")
    assert not network._valid_target("example.com;whoami")
    assert not network._valid_target("example.com && id")
    assert not network._valid_target("$(hostname)")
    assert not network._valid_target("-example.com")


def test_invalid_arguments_return_usage():
    assert network.dns("example.com;id") == "Usage: !dns <hostname>"
    assert network.whois("") == "Usage: !whois <domain>"
    assert network.ping("8.8.8.8 && id") == (
        "Usage: !ping <hostname-or-ip>"
    )
    assert network.trace("one two") == (
        "Usage: !trace <hostname-or-ip>"
    )
