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

The IRC transport supports TLS with certificate validation when configured; the legacy default can still use plaintext IRC. Do not send sensitive information over plaintext IRC.

The current IRC implementation does not provide:

- IRC account authentication as a complete operator identity solution
- General per-user authorization beyond the scoped operator HMAC flow
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

## Public repository threat model

- Public source code, historical commits, example Terraform, workflow logs, and published images are visible to potential adversaries. Never place real IP addresses, identity hostmasks, cloud account identifiers, credential values, inventory exports, or unredacted infrastructure logs in public examples.
- The API is intended for loopback access. Binding to a non-loopback interface requires both Basic Auth environment values; terminate TLS at a trusted reverse proxy and restrict access with network controls. Basic Auth alone is not secure over plaintext HTTP.
- The local gateway collector currently disables certificate verification for a home-gateway compatibility case. Keep it constrained to a trusted LAN; do not adapt that fetch mechanism for Internet endpoints.
- GitHub Actions ECR credentials should be restricted to the intended protected branch and least-privilege image repository. Review live AWS IAM policies after any Terraform change; updating code does not update AWS until explicitly applied.
- Once material is committed to a public repository, deleting or replacing it in the latest tree does not remove the historical exposure. Rotate any real credentials that might have appeared and assess whether history remediation is warranted.

## Recommended deployment review

Audit the Pi firewall/listening ports, Docker socket access, systemd environment-file permissions, IRC TLS/certificate settings, API reverse proxy and network exposure, GitHub branch protection, AWS OIDC role trust, and secrets/Dependency scanning alerts before treating a deployment as hardened.
