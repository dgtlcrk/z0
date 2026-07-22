# Security Policy

## Supported versions

z0 is currently an early-stage project.

Security fixes are applied to the latest development release.

| Version | Supported |
|---|---|
| Latest 1.x release | Yes |
| Older releases | No |

## Reporting a vulnerability

Do not disclose suspected vulnerabilities in a public issue, discussion, pull
request, or IRC channel.

Use GitHub's private vulnerability reporting or Security Advisory feature when
it is available for this repository.

A useful report should include:

- A description of the issue
- The affected version or commit
- Reproduction steps
- Potential impact
- Relevant logs or output with secrets removed
- A suggested fix, when known

Do not include credentials, private keys, access tokens, or sensitive personal
information in a report.

## Response expectations

The project maintainer will attempt to:

1. Acknowledge a valid report.
2. Reproduce and assess the issue.
3. Develop and test a fix.
4. Publish an updated release when appropriate.
5. Credit the reporter unless anonymity is requested.

Response times are not guaranteed because the project is independently
maintained.

## Current security limitations

The current IRC implementation does not provide:

- TLS configuration
- IRC account authentication
- Per-user authorization
- Per-command access controls
- Rate limiting
- Targeted command routing between multiple bot instances

Do not expose privileged operations, credentials, or sensitive system data
through the current command interface.

## Network-command safety

z0 can generate DNS, WHOIS, ICMP, and traceroute traffic.

Network targets are validated before external utilities are invoked, and
commands are executed without shell interpolation. These protections do not
replace operator authorization or responsible use.

Only use z0 against systems and networks where you have permission.

## Deployment security

Operators should:

- Keep secrets outside the repository
- Protect local `.env` files
- Keep Terraform state private
- Use least-privilege cloud permissions
- Use AWS Systems Manager instead of exposing administrative ports
- Keep the host, container image, and Python dependencies updated
- Review logs before sharing them publicly
