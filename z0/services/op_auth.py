"""One-time HMAC authentication for IRC operator requests."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass


@dataclass
class PendingChallenge:
    nonce: str
    channel: str
    expires_at: float
    attempts: int = 0


class OpAuthenticator:
    def __init__(self, secret: str, channel: str, *, ttl: int = 90) -> None:
        if len(secret) < 32:
            raise ValueError("IRC_OP_SECRET must contain at least 32 characters")
        self._secret = secret.encode("utf-8")
        self.channel = channel
        self.ttl = ttl
        self.pending: dict[str, PendingChallenge] = {}
        self.last_request: dict[str, float] = {}

    @staticmethod
    def _identity(source: str) -> str:
        return source.lower()

    def challenge(self, source: str, channel: str) -> tuple[bool, str]:
        if channel.lower() != self.channel.lower():
            return False, "Channel not authorized"
        now = time.monotonic()
        identity = self._identity(source)
        if now - self.last_request.get(identity, -float("inf")) < 10:
            return False, "Wait before requesting another challenge"
        self.last_request[identity] = now
        nonce = secrets.token_hex(24)
        self.pending[identity] = PendingChallenge(nonce, channel, now + self.ttl)
        return True, f"Challenge for {channel}: {nonce} (expires in {self.ttl}s)"

    def verify(self, source: str, channel: str, digest: str) -> bool:
        identity = self._identity(source)
        pending = self.pending.get(identity)
        if not pending:
            return False
        if time.monotonic() >= pending.expires_at or pending.channel.lower() != channel.lower():
            self.pending.pop(identity, None)
            return False
        pending.attempts += 1
        if pending.attempts >= 3:
            self.pending.pop(identity, None)
        if len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            return False
        payload = f"z0-op-v1:{channel.lower()}:{pending.nonce}".encode()
        expected = hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
        valid = hmac.compare_digest(expected, digest.lower())
        if valid:
            self.pending.pop(identity, None)
        return valid
