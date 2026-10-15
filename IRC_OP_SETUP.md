# IRC operator authentication

This feature is **disabled by default**. Set `IRC_OP_SECRET` only on the trusted host running the IRC bot. The existing `IRC_CHANNEL` controls which channel can be granted OP.

## Generate a secret

On a trusted device:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Keep the generated value in a password manager and in the protected EC2 `/path/to/protected/bot.env` file (mode 0600). **Never commit or share the secret.** The environment file is loaded by Docker at container creation; editing it alone does not alter the running container.

## Use

1. In WeeChat, send `/msg YOUR_BOT_NICK op #YOUR_CHANNEL` (use the bot's actual nickname).
2. The bot replies privately with a random 48-character hexadecimal nonce.
3. On your own trusted terminal, run `python tools/op_response.py '#YOUR_CHANNEL' NONCE`.
4. The helper prompts for the secret without echo and prints `/msg YOUR_BOT_NICK op #YOUR_CHANNEL DIGEST`. Paste that line into WeeChat within 90 seconds.
5. Check your status with `/names #YOUR_CHANNEL`.

Each challenge is bound to the requester's full IRC prefix (`nick!user@host`), limited to three verification attempts, rate-limited for new challenges, and single-use. The bot must itself be an operator to grant +o. Only the configured channel is permitted.

## Deployment

Build a **new immutable ECR image tag** from a reviewed commit. Do not overwrite the currently deployed immutable image tag. Retain the Docker container's existing environment, `--env-file /path/to/protected/bot.env`, restart policy, and its rollback image. Check the bot's actual nickname before initiating requests.

No secret may be committed to this public repository, passed in chat, or included in bot logging.

## Security limitations

The authentication protocol does not reveal the shared secret on IRC, but EFnet connections using port 6667 are generally plaintext and vulnerable to active interception. Prefer verified TLS for both clients when supported. This protocol authorizes **anyone holding the shared secret**, not a permanent verified IRC account. Rotate the secret if exposed, and consider further protections before public production use.
