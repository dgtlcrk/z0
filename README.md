# z0

z0 is a container-first IRC network automation and diagnostics bot written in
Python.

It provides lightweight system and network commands through IRC and supports
multiple deployments from the same codebase. An on-premises instance can run
as `z0`, while a cloud-hosted instance can run as `digitalcrack`, with identity
and connection settings supplied entirely through environment variables.

> Project status: early-stage and actively developed.

## Features

- Environment-driven bot identity
- IRC command handling
- Process uptime reporting
- Linux system information
- DNS resolution
- WHOIS summaries
- ICMP ping
- Limited traceroute
- Hostname and IP-address validation
- Safe subprocess execution without shell interpolation
- IRC response splitting for long command output
- Non-root Docker container
- Automated Python tests and linting
- Raspberry Pi and AWS deployment support

## Architecture

```text
IRC user
   |
   | !command
   v
IRC network
   |
   v
z0.services.irc
   |
   +-- z0.commands.core
   +-- z0.commands.system
   +-- z0.commands.network
           |
           +-- Python standard library
           +-- ping
           +-- traceroute
           +-- whois
```

The same application image can run under different identities:

```text
Raspberry Pi                     AWS EC2
-------------                    -------
BOT_NAME=z0                      BOT_NAME=digitalcrack
IRC_NICK=z0                      IRC_NICK=digitalcrack
       |                                  |
       +----------- same code ------------+
```

## Available commands

| Command | Description |
|---|---|
| `!help` | List available commands |
| `!ping` | Return `PONG` |
| `!uptime` | Show bot process uptime |
| `!about` | Show application identity and Python version |
| `!hostname` | Show the container hostname |
| `!time` | Show the container's current local time |
| `!version` | Show Python, kernel, and CPU architecture |
| `!memory` | Show Linux memory utilization |
| `!disk` | Show root filesystem utilization |
| `!dns <host>` | Resolve IPv4 and IPv6 addresses |
| `!whois <domain>` | Return a compact WHOIS summary |
| `!ping <host>` | Send four ICMP echo requests |
| `!trace <host>` | Run a limited eight-hop traceroute |

When multiple instances are connected to the same IRC channel, each instance
currently responds to every supported command.

## Requirements

Docker is the recommended runtime.

For direct Python execution:

- Python 3.12 or newer
- Linux for `/proc/meminfo` reporting
- `ping`
- `traceroute`
- `whois`

## Quick start with Docker

Clone the repository:

```bash
git clone https://github.com/dgtlcrk/z0.git
cd z0
```

Create local configuration:

```bash
cp .env.example .env
```

Edit `.env`:

```ini
BOT_NAME=z0
IRC_SERVER=irc.example.net
IRC_PORT=6667
IRC_NICK=z0
IRC_CHANNEL=#automation
```

Build the image:

```bash
docker build -t z0:local .
```

Start the bot:

```bash
docker run -d \
  --name z0 \
  --hostname z0 \
  --restart unless-stopped \
  --env-file .env \
  z0:local
```

View logs:

```bash
docker logs -f z0
```

Stop and remove the container:

```bash
docker rm -f z0
```

## Local development

Create a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install the project and development tools:

```bash
python -m pip install --upgrade pip
python -m pip install -e . -r requirements-dev.txt
```

Run the application:

```bash
python -m z0.main
```

The package also installs a console command:

```bash
z0
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `BOT_NAME` | `z0` | Identity shown in logs and `!about` |
| `IRC_SERVER` | `irc.prison.net` | IRC server hostname |
| `IRC_PORT` | `6667` | IRC server port |
| `IRC_NICK` | `BOT_NAME` | IRC nickname |
| `IRC_CHANNEL` | `#skipland` | Channel joined after connecting |

The application automatically loads a local `.env` file when present.

The `.env` file is excluded from Git. Never commit credentials, private keys,
IRC passwords, Terraform state, or live Terraform variable files.
## Multiple runtime identities

On-premises configuration:

```ini
BOT_NAME=z0
IRC_NICK=z0
```

Cloud configuration:

```ini
BOT_NAME=digitalcrack
IRC_NICK=digitalcrack
```

No source-code changes are required between deployments.

## Testing

Run the full local validation suite:

```bash
python -m compileall -q z0
python -m ruff check .
python -m pytest
docker build -t z0:test .
```

Current automated coverage includes:

- Environment configuration
- Bot-name and nickname behavior
- Core command output
- Process uptime formatting
- Network-target validation
- Rejection of shell-injection-style input

## Repository layout

```text
z0/
|-- .github/
|   `-- workflows/
|-- infrastructure/
|   `-- terraform/
|-- tests/
|-- z0/
|   |-- commands/
|   |   |-- core.py
|   |   |-- network.py
|   |   `-- system.py
|   |-- services/
|   |   `-- irc.py
|   |-- config.py
|   `-- main.py
|-- Dockerfile
|-- pyproject.toml
|-- requirements.txt
`-- requirements-dev.txt
```

Live deployment-specific Terraform configuration, state, plans, and variable
files are intentionally excluded from version control.

## Security considerations

The network commands create real DNS, WHOIS, ICMP, and traceroute traffic.
Only use them against systems and networks where you have authorization.

The current IRC implementation does not yet provide:

- TLS configuration
- IRC account authentication
- Per-user command authorization
- Per-command access controls
- Targeted commands for channels containing multiple bot instances

Do not expose privileged or sensitive operations through the current command
interface.

## Project roadmap

Planned improvements include:

- IRC TLS support
- Authentication and command authorization
- Targeted commands for multi-bot channels
- Structured logging
- Expanded tests
- Reusable public Terraform deployment examples
- Automated cloud deployment from private repositories

## Contributing

Contribution instructions will be maintained in
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Security reports

Security reporting instructions will be maintained in
[`SECURITY.md`](SECURITY.md).

## Changelog

Release history is available in [`CHANGELOG.md`](CHANGELOG.md).

## Author

Created and maintained by **Lorenzo Brown**
([@dgtlcrk](https://github.com/dgtlcrk)).

## License

Licensed under the Apache License, Version 2.0.

See [`LICENSE`](LICENSE) for the complete license terms.
