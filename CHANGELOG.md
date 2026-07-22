# Changelog

All notable changes to z0 are documented in this file.

The project uses semantic versioning for release tags.

## Unreleased

### Planned

- IRC TLS support
- Authentication and command authorization
- Targeted commands for channels containing multiple bot instances
- Structured logging
- Reusable public AWS deployment examples
- Expanded automated testing
- Automated private-repository cloud deployment

## 1.1.0 - 2026-07-22

### Added

- Environment-driven `BOT_NAME`
- Independent runtime identities for on-premises and cloud deployments
- `IRC_NICK` fallback to `BOT_NAME`
- Python package metadata
- Installable `z0` console entry point
- Ruff lint configuration
- Automated configuration tests
- Automated core-command tests
- Automated network-input validation tests
- Comprehensive project README
- Apache License 2.0

### Changed

- `!about` now reports the configured application identity
- Startup logs now report the configured application identity
- IRC real-name metadata now uses the configured application identity
- Local environment and Terraform ignore rules were strengthened

### Security

- Network targets are validated before invoking external utilities
- Network commands use argument lists without shell interpolation
- Docker continues to run the application as a non-root user

### Verified

- Raspberry Pi deployment running as `z0`
- AWS deployment running as `digitalcrack`
- Shared source code and Docker image operating under separate identities
- Python compilation passes
- Ruff lint checks pass
- Nine automated tests pass

## 1.0.0

### Added

- Modular Python package structure
- Environment-based IRC configuration
- IRC connectivity and automatic channel join
- Automatic IRC reconnection
- Safe splitting of long IRC responses
- Core commands:
  - `!help`
  - `!ping`
  - `!uptime`
  - `!about`
- Linux system commands:
  - `!hostname`
  - `!time`
  - `!version`
  - `!memory`
  - `!disk`
- Network commands:
  - `!dns`
  - `!whois`
  - `!ping <host>`
  - `!trace <host>`
- Docker image containing `ping`, `traceroute`, and `whois`
- Non-root Docker execution
- GitHub Actions ECR build pipeline
- Terraform bootstrap infrastructure
