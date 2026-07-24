# Changelog

All notable changes to z0 are documented in this file.

The project uses semantic versioning for release tags.

## Unreleased
## 1.1.1 - 2026-07-24

### Added

- Human-readable output for `z0 status`
- Human-readable adapter, plugin, and scheduler job output
- `--json` support for platform status, adapters, plugins, and jobs
- `z0 version` and `z0 --version`
- Reproducible systemd units for the API and scheduler
- Updated platform-focused README
- Expanded automated CLI and API tests

### Fixed

- Git repository detection no longer reports `site-packages`
- API and CLI now use one centralized package version
- Legacy environment configuration remains compatible with centralized TOML settings
- Scheduler service now runs continuously and updates job timestamps
- Python build artifacts are ignored by Git

### Changed

- `z0 status` now displays the operator dashboard by default
- JSON is now opt-in using `--json`
- API version responses now use the full semantic version
- Project documentation now describes z0_n3t as an operations and network automation platform

### Verified

- 56 automated tests pass
- API and scheduler services are active
- Infrastructure health executes every five minutes
- Docker operations remain functional
- Raspberry Pi deployment verified on Ubuntu 24.04 LTS

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
