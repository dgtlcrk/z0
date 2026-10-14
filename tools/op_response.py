"""Compute an IRC OP challenge response locally without transmitting the secret."""
import getpass
import hashlib
import hmac
import sys

if len(sys.argv) != 3:
    raise SystemExit("Usage: python tools/op_response.py '#skipland' NONCE")

channel, nonce = sys.argv[1:]
if len(nonce) != 48 or any(c not in "0123456789abcdef" for c in nonce):
    raise SystemExit("Invalid challenge nonce")
secret = getpass.getpass("IRC OP secret: ")
response = hmac.new(
    secret.encode(),
    f"z0-op-v1:{channel.lower()}:{nonce}".encode(),
    hashlib.sha256,
).hexdigest()
print(f"/msg digitalcr op {channel} {response}")
