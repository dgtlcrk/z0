import hashlib
import hmac

from z0.services.op_auth import OpAuthenticator


def test_challenge_and_one_time_response():
    auth = OpAuthenticator("s" * 32, "#skipland")
    ok, message = auth.challenge("nas-!user@host", "#skipland")
    assert ok
    nonce = message.split(": ", 1)[1].split()[0]
    digest = hmac.new(
        b"s" * 32,
        f"z0-op-v1:#skipland:{nonce}".encode(),
        hashlib.sha256,
    ).hexdigest()
    assert not auth.verify("other!user@host", "#skipland", digest)
    assert auth.verify("nas-!user@host", "#skipland", digest)
    assert not auth.verify("nas-!user@host", "#skipland", digest)


def test_wrong_channel_and_throttling():
    auth = OpAuthenticator("s" * 32, "#skipland")
    assert not auth.challenge("nas!u@h", "#other")[0]
    assert auth.challenge("nas!u@h", "#skipland")[0]
    assert not auth.challenge("nas!u@h", "#skipland")[0]
    assert not auth.verify("nas!u@h", "#other", "a" * 64)


def test_short_secret_rejected():
    try:
        OpAuthenticator("short", "#skipland")
    except ValueError:
        pass
    else:
        raise AssertionError("weak secret accepted")
