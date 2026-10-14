"""IRC alert validation accepts normal text, rejects control characters."""

import pytest

from z0.services.irc import valid_irc_alert_message


def test_valid_normal_irc_alerts():
    assert valid_irc_alert_message(
        "z0_n3t TEST: IRC alert delivery operational. No actual outage."
    )
    assert valid_irc_alert_message(
        "z0_n3t DOWN: 192.168.1.254 (AVAILABLE -> UNAVAILABLE)"
    )


@pytest.mark.parametrize("char", ["\r", "\n", "\x00"])
def test_reject_irc_control_characters(char):
    assert not valid_irc_alert_message("z0_n3t TEST: x" + char + "y")


def test_reject_invalid_payloads():
    assert not valid_irc_alert_message("untrusted message")
    assert not valid_irc_alert_message(None)
    assert not valid_irc_alert_message("z0_n3t " + "a" * 350)
