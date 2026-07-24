# z0_n3t

z0_n3t is a Python-based network automation and operations platform running on
Linux, Docker, and Raspberry Pi.

The platform provides a unified command-line interface, system inventory,
infrastructure health checks, scheduled plugin execution, Docker operations,
an HTTP API, and IRC/BotOps integration.

## Current Capabilities

- Human-readable platform status dashboard
- JSON output for automation
- Raspberry Pi and Linux system inventory
- Service and infrastructure health monitoring
- Plugin discovery and execution
- Persistent scheduler jobs
- Docker engine and container operations
- HTTP JSON API
- IRC/BotOps runtime
- Prometheus, Grafana, and Jenkins integration
- Installable Python console commands
- Automated tests and input validation

## Runtime Architecture

```text
Raspberry Pi host
|
|-- z0-api.service
|   `-- z0-platform api
|       `-- HTTP API on 127.0.0.1:8081
|
|-- z0-scheduler.service
|   `-- z0-platform jobs daemon --poll 5
|       `-- Executes scheduled plugin jobs
|
`-- Docker
    |-- z0         IRC/BotOps runtime
    |-- prometheus Metrics collection
    |-- grafana    Monitoring dashboards
    `-- jenkins    Automation server
```

## Requirements

- Python 3.12 or newer
- Linux
- Git
- Docker
- Python virtual environment support

The current primary deployment runs on Ubuntu 24.04 LTS on a Raspberry Pi 4.

## Installation

Clone the repository:

```bash
git clone https://github.com/dgtlcrk/z0.git
cd z0
```

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project and development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e . -r requirements-dev.txt
```

Verify the installation:

```bash
z0 version
z0 --help
```

## Command-Line Interface

### Platform status

```bash
z0 status
```

Machine-readable output:

```bash
z0 status --json
```

### Adapters

```bash
z0 adapters
z0 adapters --json
```

### Plugins

```bash
z0 plugins
z0 plugins --json
```

### Scheduler

```bash
z0 jobs list
z0 jobs list --json
```

### Version

```bash
z0 version
z0 --version
```

## Docker Operations

Show Docker engine status:

```bash
z0 docker status
```

List running containers:

```bash
z0 docker ps
```

Include stopped containers:

```bash
z0 docker ps --all
```

Show Docker engine information:

```bash
z0 docker info
```

Show container resource usage:

```bash
z0 docker stats
z0 docker stats jenkins
```

Inspect a container:

```bash
z0 docker inspect CONTAINER
```

View container logs:

```bash
z0 docker logs CONTAINER
z0 docker logs CONTAINER --tail 50
```

Restart a container:

```bash
z0 docker restart CONTAINER
```

## HTTP API

The API listens locally on:

```text
http://127.0.0.1:8081
```

Check the API:

```bash
curl -s http://127.0.0.1:8081/ | python -m json.tool
```

Available endpoints include:

```text
/api/status
/api/system
/api/inventory
/api/services
/api/health
/api/adapters
/api/plugins
/api/jobs
/api/project
/api/docker
/api/docker/info
/api/docker/inspect
/api/docker/stats
/api/docker/logs
```

## Systemd Services

The API runs under:

```text
z0-api.service
```

The scheduler runs under:

```text
z0-scheduler.service
```

Check both services:

```bash
sudo systemctl status z0-api --no-pager
sudo systemctl status z0-scheduler --no-pager
```

Restart them:

```bash
sudo systemctl restart z0-api z0-scheduler
```

View logs:

```bash
sudo journalctl -u z0-api -n 100 --no-pager
sudo journalctl -u z0-scheduler -n 100 --no-pager
```

Systemd unit files are stored in:

```text
deploy/systemd/
```

## Configuration

Platform defaults are stored in:

```text
z0/config/default.toml
```

BotOps host configuration is loaded from:

```text
~/.config/z0/botops.env
```

The Docker IRC/BotOps runtime uses environment variables from the local
`.env` file.

Never commit credentials, passwords, private keys, Terraform state, or live
environment files.

## Development

Activate the virtual environment:

```bash
cd ~/projects/z0
source .venv/bin/activate
```

Run the test suite:

```bash
python -m pytest
```

Run Ruff against files being changed:

```bash
python -m ruff check PATHS...
```

Check for whitespace errors:

```bash
git diff --check
```

Install the current source into the virtual environment:

```bash
pip install --force-reinstall --no-deps .
hash -r
```

Restart long-running services after installation:

```bash
sudo systemctl restart z0-api z0-scheduler
```

## Repository Layout

```text
z0/
|-- deploy/
|   `-- systemd/
|       |-- z0-api.service
|       `-- z0-scheduler.service
|-- docs/
|-- tests/
|-- z0/
|   |-- adapters/
|   |-- api/
|   |-- botops/
|   |-- config/
|   |-- core/
|   |-- dockerops/
|   |-- plugins/
|   |-- scheduler/
|   |-- docker_cli.py
|   |-- platform_cli.py
|   `-- unified_cli.py
|-- Dockerfile
|-- pyproject.toml
|-- README.md
`-- CHANGELOG.md
```

## Security

Network diagnostics and future discovery features must only be used against
systems and networks where authorization has been granted.

The API currently binds to `127.0.0.1`. Do not expose it publicly without
authentication, authorization, TLS, and appropriate network controls.

Do not expose Docker restart, logs, inspection, or future device-configuration
operations to untrusted users.

## Roadmap

The next development phase focuses on network discovery and persistent device
inventory.

Planned commands include:

```text
z0 discover
z0 discover --subnet 192.168.1.0/24
z0 inventory list
z0 inventory show DEVICE
z0 device status DEVICE
```

Later phases will add:

- SSH device execution
- Cisco automation
- Palo Alto integration
- F5 integration
- AWS nodes
- Multi-node management
- Web dashboard

## Documentation

Release history is maintained in:

```text
CHANGELOG.md
```

## Author

Created and maintained by **Lorenzo Brown**
GitHub: **dgtlcrk**

## License

Licensed under the Apache License, Version 2.0.

See `LICENSE` for the complete license terms.
